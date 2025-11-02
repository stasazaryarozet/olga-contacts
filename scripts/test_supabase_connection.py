"""
Test PostgreSQL connection to Supabase and import data
"""

import sys
import psycopg2
from pathlib import Path

# Connection string (trying pooler)
DATABASE_URL = "postgresql://postgres.lzwmoicxwrjgqmxfltcq:NJtdpocY0oTbSZdI@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

print("🔌 Connecting to Supabase PostgreSQL...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Connected successfully!")
    
    cursor = conn.cursor()
    
    # Test query
    cursor.execute("SELECT version()")
    version = cursor.fetchone()
    print(f"📊 PostgreSQL version: {version[0][:50]}...")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Connection test passed!")
    print("Ready to import schema and data.")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

