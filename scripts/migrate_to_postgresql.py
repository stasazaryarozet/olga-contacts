"""
Migration script: SQLite → PostgreSQL (Supabase)
Exports all data from contacts_v2.db and generates SQL INSERT statements
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def export_table_to_sql(cursor, table_name, output_file):
    """Export table data to SQL INSERT statements."""
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ⚠️ Table {table_name} is empty")
        return 0
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    columns_str = ", ".join(columns)
    
    # Filter out auto-increment columns for INSERT
    insert_columns = [col for col in columns if col not in ['entity_id', 'edge_id', 'source_id', 'raw_id']]
    insert_columns_str = ", ".join(insert_columns)
    
    output_file.write(f"\n-- {table_name.upper()} ({len(rows)} rows)\n")
    
    for row in rows:
        # Create dict from row
        row_dict = dict(zip(columns, row))
        
        # Filter values for non-auto-increment columns
        values = []
        for col in insert_columns:
            val = row_dict[col]
            if val is None:
                values.append("NULL")
            elif isinstance(val, str):
                # Escape single quotes
                escaped = val.replace("'", "''")
                values.append(f"'{escaped}'")
            elif isinstance(val, (int, float)):
                values.append(str(val))
            else:
                values.append(f"'{val}'")
        
        values_str = ", ".join(values)
        output_file.write(f"INSERT INTO {table_name} ({insert_columns_str}) VALUES ({values_str});\n")
    
    return len(rows)


def main():
    """Main migration function."""
    print("=" * 60)
    print("🔄 MIGRATION: SQLite → PostgreSQL")
    print("=" * 60)
    print()
    
    db_path = "data/contacts_v2.db"
    output_path = "migration_data.sql"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    print(f"📂 Source: {db_path}")
    print(f"📄 Output: {output_path}")
    print()
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Open output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("-- PostgreSQL Migration Data\n")
        f.write(f"-- Generated: {Path(db_path).stat().st_mtime}\n")
        f.write("-- Source: SQLite (contacts_v2.db)\n")
        f.write("-- Target: PostgreSQL (Supabase)\n")
        f.write("\n")
        f.write("BEGIN;\n\n")
        
        # Export tables in order (respecting foreign keys)
        tables = [
            'sources',
            'entities',
            'identifiers',
            'edges',
            'raw_data'
        ]
        
        total_rows = 0
        for table in tables:
            print(f"📊 Exporting {table}...")
            try:
                count = export_table_to_sql(cursor, table, f)
                print(f"  ✅ Exported {count} rows")
                total_rows += count
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
        
        f.write("\nCOMMIT;\n")
        
        # Reset sequences (for SERIAL columns)
        f.write("\n-- Reset sequences\n")
        f.write("SELECT setval('entities_entity_id_seq', (SELECT MAX(entity_id) FROM entities));\n")
        f.write("SELECT setval('edges_edge_id_seq', (SELECT MAX(edge_id) FROM edges));\n")
        f.write("SELECT setval('sources_source_id_seq', (SELECT MAX(source_id) FROM sources));\n")
        f.write("SELECT setval('raw_data_raw_id_seq', (SELECT MAX(raw_id) FROM raw_data));\n")
    
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ Migration complete: {total_rows} total rows")
    print(f"📄 SQL file: {output_path}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Create Supabase project")
    print("2. Run schema_postgresql.sql in Supabase SQL Editor")
    print("3. Run migration_data.sql in Supabase SQL Editor")
    print("4. Update enhanced_graph_db.py to use PostgreSQL")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

