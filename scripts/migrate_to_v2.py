"""
Migrate from contacts_enhanced.db to contacts_v2.db with new schema
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Remove old db import, create new one
import sqlite3


def migrate_to_v2():
    """Migrate to v2 schema with business contact fields."""
    
    print("🔄 Миграция: contacts_enhanced.db → contacts_v2.db")
    print()
    
    old_db_path = "data/contacts_enhanced.db"
    new_db_path = "data/contacts_v2.db"
    
    # Backup old
    if Path(old_db_path).exists():
        backup_path = f"data/contacts_enhanced_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(old_db_path, backup_path)
        print(f"  ✓ Backup: {backup_path}")
    
    # Create new DB with enhanced_graph_db
    from enhanced_graph_db import EnhancedGraphDB
    new_db = EnhancedGraphDB(new_db_path)
    
    # Connect to old DB
    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    
    print()
    print("📦 Миграция данных...")
    print()
    
    # 1. Migrate entities
    cursor = old_conn.execute("SELECT * FROM entities")
    entities = cursor.fetchall()
    
    print(f"  1️⃣  Entities: {len(entities)}")
    
    for entity in entities:
        new_db.conn.execute("""
            INSERT INTO entities (entity_id, label, type, created_at)
            VALUES (?, ?, ?, ?)
        """, (entity['entity_id'], entity['label'], entity['type'], entity['created_at']))
    
    new_db.conn.commit()
    
    # 2. Migrate identifiers
    cursor = old_conn.execute("SELECT * FROM identifiers")
    identifiers = cursor.fetchall()
    
    print(f"  2️⃣  Identifiers: {len(identifiers)}")
    
    for identifier in identifiers:
        new_db.conn.execute("""
            INSERT INTO identifiers (identifier, entity_id, identifier_type, created_at)
            VALUES (?, ?, ?, ?)
        """, (identifier['identifier'], identifier['entity_id'], 
              identifier['identifier_type'], identifier['created_at']))
    
    new_db.conn.commit()
    
    # 3. Migrate sources
    cursor = old_conn.execute("SELECT * FROM sources")
    sources = cursor.fetchall()
    
    print(f"  3️⃣  Sources: {len(sources)}")
    
    for source in sources:
        new_db.conn.execute("""
            INSERT INTO sources (source_id, filename, source_type, hash, processed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (source['source_id'], source['filename'], source['source_type'],
              source['hash'], source['processed_at']))
    
    new_db.conn.commit()
    
    # 4. Migrate raw_data
    cursor = old_conn.execute("SELECT * FROM raw_data")
    raw_data = cursor.fetchall()
    
    print(f"  4️⃣  Raw Data: {len(raw_data)}")
    
    for data in raw_data:
        new_db.conn.execute("""
            INSERT INTO raw_data (raw_id, source_id, data_type, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (data['raw_id'], data['source_id'], data['data_type'],
              data['content'], data['created_at']))
    
    new_db.conn.commit()
    
    # 5. Migrate edges
    cursor = old_conn.execute("SELECT * FROM edges")
    edges = cursor.fetchall()
    
    print(f"  5️⃣  Edges: {len(edges)}")
    
    for edge in edges:
        new_db.conn.execute("""
            INSERT INTO edges (edge_id, subject_id, object_id, relation_type, 
                             event_date, confidence, source_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (edge['edge_id'], edge['subject_id'], edge['object_id'],
              edge['relation_type'], edge['event_date'], edge['confidence'],
              edge['source_id'], edge['created_at']))
    
    new_db.conn.commit()
    
    print()
    print("✅ Миграция базовых данных завершена")
    print()
    
    # Close
    old_conn.close()
    new_db.close()
    
    print(f"🎯 Новая БД: {new_db_path}")
    print()
    
    # Now enrich
    print("🔧 Обогащение entities...")
    print()
    
    new_db = EnhancedGraphDB(new_db_path)
    
    cursor = new_db.conn.execute("SELECT entity_id FROM entities")
    entity_ids = [row[0] for row in cursor.fetchall()]
    
    now = datetime.now()
    enriched = 0
    
    for entity_id in entity_ids:
        # 1. primary_identifier
        cursor = new_db.conn.execute("""
            SELECT identifier FROM identifiers 
            WHERE entity_id = ? 
            LIMIT 1
        """, (entity_id,))
        
        result = cursor.fetchone()
        primary_identifier = result[0] if result else None
        
        # 2. first_seen
        cursor = new_db.conn.execute("""
            SELECT MIN(event_date) FROM edges 
            WHERE subject_id = ? OR object_id = ?
        """, (entity_id, entity_id))
        
        first_seen = cursor.fetchone()[0]
        
        # 3. last_interaction
        cursor = new_db.conn.execute("""
            SELECT MAX(event_date) FROM edges 
            WHERE subject_id = ? OR object_id = ?
        """, (entity_id, entity_id))
        
        last_interaction = cursor.fetchone()[0]
        
        # 4. relationship_strength (degree / max_degree)
        cursor = new_db.conn.execute("""
            SELECT COUNT(DISTINCT edge_id) FROM edges 
            WHERE (subject_id = ? OR object_id = ?)
        """, (entity_id, entity_id))
        
        degree = cursor.fetchone()[0]
        
        # Get max degree
        cursor = new_db.conn.execute("""
            SELECT MAX(cnt) FROM (
                SELECT COUNT(DISTINCT edge_id) as cnt
                FROM edges
                GROUP BY subject_id
                UNION ALL
                SELECT COUNT(DISTINCT edge_id) as cnt
                FROM edges
                GROUP BY object_id
            )
        """)
        max_degree = cursor.fetchone()[0] or 1
        
        relationship_strength = round(degree / max_degree, 3) if max_degree > 0 else 0.0
        
        # 5. status
        status = 'unknown'
        if last_interaction:
            try:
                last_date = datetime.fromisoformat(last_interaction)
                days_since = (now - last_date).days
                
                if days_since <= 180:
                    status = 'active'
                elif days_since >= 730:
                    status = 'cold'
            except:
                pass
        
        # Update
        new_db.conn.execute("""
            UPDATE entities SET
                primary_identifier = ?,
                first_seen = ?,
                last_interaction = ?,
                relationship_strength = ?,
                status = ?,
                updated_at = ?
            WHERE entity_id = ?
        """, (primary_identifier, first_seen, last_interaction,
              relationship_strength, status, datetime.now().isoformat(), entity_id))
        
        enriched += 1
        if enriched % 50 == 0:
            new_db.conn.commit()
            print(f"  ✓ Обогащено {enriched}/{len(entity_ids)}")
    
    new_db.conn.commit()
    
    print()
    print(f"✅ Обогащено: {enriched} entities")
    print()
    
    # Stats
    cursor = new_db.conn.execute("SELECT status, COUNT(*) FROM entities GROUP BY status")
    print("📊 Status:")
    for status, count in cursor.fetchall():
        print(f"  • {status}: {count}")
    
    print()
    
    new_db.close()


if __name__ == "__main__":
    migrate_to_v2()

