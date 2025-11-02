============================================================
🔄 MIGRATION: SQLite → PostgreSQL
============================================================

📂 Source: data/contacts_v2.db
📄 Output: migration_data.sql

📊 Exporting sources...
  ✅ Exported 460 rows
📊 Exporting entities...
  ✅ Exported 464 rows
📊 Exporting identifiers...
  ✅ Exported 464 rows
📊 Exporting edges...
  ✅ Exported 5050 rows
📊 Exporting raw_data...
  ✅ Exported 460 rows

============================================================
✅ Migration complete: 6898 total rows
📄 SQL file: migration_data.sql
============================================================

Next steps:
1. Create Supabase project
2. Run schema_postgresql.sql in Supabase SQL Editor
3. Run migration_data.sql in Supabase SQL Editor
4. Update enhanced_graph_db.py to use PostgreSQL
