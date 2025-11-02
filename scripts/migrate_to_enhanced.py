"""
Migration script: Transfer data from old graph_db.py to enhanced_graph_db.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from graph_db import GraphDB
from enhanced_graph_db import EnhancedGraphDB


def migrate():
    """Migrate data from old to enhanced database."""
    
    print("📦 Миграция: graph_db.py → enhanced_graph_db.py")
    print()
    
    # Open old database
    old_db = GraphDB()
    
    # Create new database
    new_db = EnhancedGraphDB()
    
    # Get all facts from old database
    cursor = old_db.conn.execute("""
        SELECT 
            f.relation_type,
            n_subj.name as subject_name,
            n_obj.name as object_name,
            f.start_date,
            f.confidence,
            f.context,
            s.url as source_url
        FROM facts f
        JOIN nodes n_subj ON f.subject_id = n_subj.canonical_id
        JOIN nodes n_obj ON f.object_id = n_obj.canonical_id
        LEFT JOIN claims c ON f.fact_id = c.fact_id
        LEFT JOIN sources s ON c.source_url = s.url
    """)
    
    facts = cursor.fetchall()
    
    print(f"🔄 Найдено {len(facts)} фактов для миграции...")
    print()
    
    # Migrate each fact
    migrated = 0
    for row in facts:
        relation_type = row[0]
        subject_name = row[1]
        object_name = row[2]
        start_date = row[3]
        confidence = row[4] or 1.0
        context = row[5]
        source_url = row[6] or 'legacy'
        
        try:
            new_db.add_fact(
                subject=subject_name,
                relation=relation_type,
                object=object_name,
                source_details={
                    'filename': source_url,
                    'type': 'legacy_migration',
                    'content': context or f"{subject_name} {relation_type} {object_name}"
                },
                event_date=start_date,
                confidence=confidence,
                subject_label=subject_name,
                object_label=object_name
            )
            migrated += 1
            
            if migrated % 100 == 0:
                print(f"  ✓ Мигрировано {migrated}/{len(facts)} фактов...")
                
        except Exception as e:
            print(f"  ✗ Ошибка при миграции факта: {subject_name} {relation_type} {object_name}")
            print(f"    {str(e)}")
    
    print()
    print(f"✅ Миграция завершена!")
    print()
    
    # Print statistics
    stats = new_db.get_stats()
    
    print("📊 Статистика новой базы данных:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Close databases
    old_db.close()
    new_db.close()
    
    print()
    print("🎯 Новая база данных: data/contacts_enhanced.db")


if __name__ == "__main__":
    migrate()

