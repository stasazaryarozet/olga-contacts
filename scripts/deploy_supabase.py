"""
Automated Supabase deployment script
Imports schema and data via SQL execution
"""

import requests
import time
import sys

# Credentials
ACCESS_TOKEN = "sbp_a02b176f867fa094f7edad75eab5f349abc8f776"
PROJECT_REF = "lzwmoicxwrjgqmxfltcq"
DB_PASSWORD = "NJtdpocY0oTbSZdI"

# API endpoints
SUPABASE_API = f"https://api.supabase.com/v1/projects/{PROJECT_REF}"
DB_URL = f"postgresql://postgres:{DB_PASSWORD}@db.{PROJECT_REF}.supabase.co:5432/postgres"

print("=" * 60)
print("🚀 SUPABASE DEPLOYMENT")
print("=" * 60)
print()

# Step 1: Test connection
print("1️⃣ Testing connection...")
try:
    import psycopg2
    conn = psycopg2.connect(DB_URL)
    print("✅ Connected to Supabase PostgreSQL")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("Trying direct connection...")
    
    DB_URL = f"postgresql://postgres:{DB_PASSWORD}@db.{PROJECT_REF}.supabase.co:5432/postgres"
    try:
        conn = psycopg2.connect(DB_URL)
        print("✅ Connected via direct URL")
        conn.close()
    except Exception as e2:
        print(f"❌ Direct connection also failed: {e2}")
        print("⏳ Project might still be initializing. Wait 2 minutes and retry.")
        sys.exit(1)

print()

# Step 2: Import schema
print("2️⃣ Importing schema...")
try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Read schema file
    with open('schema_postgresql.sql', 'r') as f:
        schema_sql = f.read()
    
    # Execute schema
    cursor.execute(schema_sql)
    conn.commit()
    
    print("✅ Schema imported (5 tables created)")
    
    # Verify tables
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    print(f"📊 Tables: {[t[0] for t in tables]}")
    
    cursor.close()
    
except Exception as e:
    print(f"❌ Schema import failed: {e}")
    conn.rollback()
    sys.exit(1)

print()

# Step 3: Import data
print("3️⃣ Importing data (6898 rows)...")
print("⏳ This may take 30-60 seconds...")

try:
    cursor = conn.cursor()
    
    # Read migration file
    with open('migration_data.sql', 'r') as f:
        migration_sql = f.read()
    
    # Execute in transaction
    cursor.execute(migration_sql)
    conn.commit()
    
    print("✅ Data imported successfully")
    
    # Verify counts
    cursor.execute("SELECT COUNT(*) FROM entities")
    entities_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM edges")
    edges_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sources")
    sources_count = cursor.fetchone()[0]
    
    print(f"📊 Imported:")
    print(f"   - {entities_count} entities")
    print(f"   - {edges_count} edges")
    print(f"   - {sources_count} sources")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Data import failed: {e}")
    conn.rollback()
    sys.exit(1)

print()
print("=" * 60)
print("✅ SUPABASE DEPLOYMENT COMPLETE")
print("=" * 60)
print()
print("Database URL (for Streamlit secrets):")
print(DB_URL)
print()
print("Next: Deploy to Streamlit Cloud")

