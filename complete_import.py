#!/usr/bin/env python3
import sqlite3
import requests
import sys

PROJECT_URL = "https://lzwmoicxwrjgqmxfltcq.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6d21vaWN4d3JqZ3FteGZsdGNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIwMzE1NTYsImV4cCI6MjA3NzYwNzU1Nn0.PEY3BRUOd0aXc22xFNz8L229DHkZAWvMVqe1Qcqntn0"

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal,resolution=merge-duplicates"
}

conn = sqlite3.connect('data/contacts_v2.db')
cursor = conn.cursor()

print("🚀 COMPLETE DATA IMPORT\n")
print("="*60)

# 1. Identifiers (all 464)
print("\n1️⃣ Identifiers (464 total)...")
cursor.execute("SELECT identifier, entity_id, identifier_type FROM identifiers")
identifiers = cursor.fetchall()

batch_size = 50
success = 0

for i in range(0, len(identifiers), batch_size):
    batch = [{"identifier": r[0], "entity_id": r[1], "identifier_type": r[2]} 
             for r in identifiers[i:i+batch_size]]
    
    try:
        response = requests.post(
            f"{PROJECT_URL}/rest/v1/identifiers", 
            headers=headers, 
            json=batch, 
            timeout=120
        )
        if response.status_code in [200, 201, 204, 409]:
            success += len(batch)
            print(f"   ✅ Batch {i//batch_size + 1}/{(len(identifiers)-1)//batch_size + 1}: {success} total")
        else:
            print(f"   ⚠️  Batch {i//batch_size + 1}: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Batch {i//batch_size + 1}: {str(e)[:50]}")

print(f"✅ Identifiers: {success}/{len(identifiers)}")

# 2. Edges (all 5050)
print("\n2️⃣ Edges (5050 total)...")
cursor.execute("SELECT subject_id, object_id, relation_type, event_date, confidence, source_id FROM edges")
edges = cursor.fetchall()

success = 0
batch_size = 25  # Smaller batches for edges (complex foreign keys)

for i in range(0, len(edges), batch_size):
    batch = []
    for r in edges[i:i+batch_size]:
        if r[0] and r[1] and r[2]:
            batch.append({
                "subject_id": r[0],
                "object_id": r[1],
                "relation_type": r[2],
                "timestamp": r[3],
                "confidence": r[4] if r[4] else 0.9,
                "source_id": r[5] if r[5] else 1
            })
    
    if not batch:
        continue
        
    try:
        response = requests.post(
            f"{PROJECT_URL}/rest/v1/edges", 
            headers=headers, 
            json=batch, 
            timeout=120
        )
        if response.status_code in [200, 201, 204, 409]:
            success += len(batch)
        
        if i % 500 == 0:
            print(f"   ✅ Progress: {success}/{len(edges)}")
            
    except Exception as e:
        if i % 500 == 0:
            print(f"   ⚠️  Progress: {success}/{len(edges)} (errors encountered)")

print(f"✅ Edges: {success}/{len(edges)}")

# 3. Raw_data (all 460)
print("\n3️⃣ Raw_data (460 total)...")
cursor.execute("SELECT source_id, entity_id, raw_text, metadata FROM raw_data")
raw_data = cursor.fetchall()

batch_size = 50
success = 0

for i in range(0, len(raw_data), batch_size):
    batch = [{"source_id": r[0], "entity_id": r[1], "raw_text": r[2], "metadata": r[3]} 
             for r in raw_data[i:i+batch_size]]
    
    try:
        response = requests.post(
            f"{PROJECT_URL}/rest/v1/raw_data", 
            headers=headers, 
            json=batch, 
            timeout=120
        )
        if response.status_code in [200, 201, 204, 409]:
            success += len(batch)
            print(f"   ✅ Batch {i//batch_size + 1}/{(len(raw_data)-1)//batch_size + 1}: {success} total")
        else:
            print(f"   ⚠️  Batch {i//batch_size + 1}: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Batch {i//batch_size + 1}: {str(e)[:50]}")

print(f"✅ Raw_data: {success}/{len(raw_data)}")

conn.close()

# Final verification
print("\n" + "="*60)
print("📊 FINAL VERIFICATION:")
print("="*60)

headers_count = {**headers, "Prefer": "count=exact"}
expected = {
    'entities': 464,
    'sources': 460,
    'identifiers': 464,
    'edges': 5050,
    'raw_data': 460
}

results = {}
for table in ['entities', 'sources', 'identifiers', 'edges', 'raw_data']:
    try:
        response = requests.head(
            f"{PROJECT_URL}/rest/v1/{table}", 
            headers=headers_count, 
            timeout=30
        )
        count = int(response.headers.get('Content-Range', '').split('/')[-1])
        results[table] = count
        status = "✅" if count >= expected[table] else "⚠️"
        print(f"   {status} {table:15s}: {count:6d}/{expected[table]} rows")
    except:
        print(f"   ❌ {table:15s}: Error")

# Check if 100% complete
all_complete = all(results.get(t, 0) >= expected[t] for t in expected.keys())

if all_complete:
    print("\n🎉 100% COMPLETE! Ready for deployment.")
    sys.exit(0)
else:
    print("\n⚠️  Partial import. Some data missing.")
    sys.exit(1)

