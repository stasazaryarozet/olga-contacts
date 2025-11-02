"""
Enrich existing entities with business contact fields
Calculates: primary_identifier, first_seen, last_interaction, relationship_strength, status
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from enhanced_graph_db import EnhancedGraphDB


def enrich_entities():
    """Enrich all entities with calculated fields."""
    
    print("🔧 Обогащение 464 entities дополнительными полями...")
    print()
    
    db = EnhancedGraphDB()
    
    # Get all entities
    cursor = db.conn.execute("SELECT entity_id, label, type FROM entities")
    entities = cursor.fetchall()
    
    print(f"📊 Найдено entities: {len(entities)}")
    print()
    
    enriched = 0
    now = datetime.now()
    
    for entity_id, label, entity_type in entities:
        # 1. Get primary_identifier (first email identifier)
        cursor = db.conn.execute("""
            SELECT identifier FROM identifiers 
            WHERE entity_id = ? AND identifier_type = 'email'
            LIMIT 1
        """, (entity_id,))
        
        primary_id_result = cursor.fetchone()
        primary_identifier = primary_id_result[0] if primary_id_result else None
        
        # 2. Get first_seen (MIN event_date)
        cursor = db.conn.execute("""
            SELECT MIN(event_date) FROM edges 
            WHERE subject_id = ? OR object_id = ?
        """, (entity_id, entity_id))
        
        first_seen_result = cursor.fetchone()
        first_seen = first_seen_result[0] if first_seen_result and first_seen_result[0] else None
        
        # 3. Get last_interaction (MAX event_date)
        cursor = db.conn.execute("""
            SELECT MAX(event_date) FROM edges 
            WHERE subject_id = ? OR object_id = ?
        """, (entity_id, entity_id))
        
        last_interaction_result = cursor.fetchone()
        last_interaction = last_interaction_result[0] if last_interaction_result and last_interaction_result[0] else None
        
        # 4. Calculate relationship_strength (degree centrality normalized)
        cursor = db.conn.execute("""
            SELECT COUNT(DISTINCT edge_id) FROM edges 
            WHERE (subject_id = ? OR object_id = ?) AND relation_type = 'co_attended'
        """, (entity_id, entity_id))
        
        degree = cursor.fetchone()[0]
        
        # Normalize: max degree in graph = 1.0
        max_degree_cursor = db.conn.execute("""
            SELECT MAX(cnt) FROM (
                SELECT entity_id, COUNT(DISTINCT edge_id) as cnt
                FROM (
                    SELECT subject_id as entity_id, edge_id FROM edges
                    UNION ALL
                    SELECT object_id as entity_id, edge_id FROM edges
                )
                GROUP BY entity_id
            )
        """)
        max_degree = max_degree_cursor.fetchone()[0] or 1
        
        relationship_strength = round(degree / max_degree, 3) if max_degree > 0 else 0.0
        
        # 5. Calculate status
        status = 'unknown'
        if last_interaction:
            try:
                last_date = datetime.fromisoformat(last_interaction)
                days_since = (now - last_date).days
                
                if days_since <= 180:  # 6 months
                    status = 'active'
                elif days_since >= 730:  # 2 years
                    status = 'cold'
                else:
                    status = 'unknown'
            except:
                status = 'unknown'
        
        # Update entity
        db.conn.execute("""
            UPDATE entities SET
                primary_identifier = ?,
                first_seen = ?,
                last_interaction = ?,
                relationship_strength = ?,
                status = ?,
                updated_at = ?
            WHERE entity_id = ?
        """, (
            primary_identifier,
            first_seen,
            last_interaction,
            relationship_strength,
            status,
            datetime.now().isoformat(),
            entity_id
        ))
        
        enriched += 1
        
        if enriched % 50 == 0:
            db.conn.commit()
            print(f"  ✓ Обогащено {enriched}/{len(entities)} entities...")
    
    db.conn.commit()
    
    print()
    print(f"✅ Обогащение завершено: {enriched} entities")
    print()
    
    # Statistics
    print("📊 Статистика обогащённых данных:")
    
    # Status distribution
    cursor = db.conn.execute("""
        SELECT status, COUNT(*) FROM entities GROUP BY status ORDER BY COUNT(*) DESC
    """)
    print("\n  Status:")
    for status, count in cursor.fetchall():
        print(f"    • {status}: {count}")
    
    # Relationship strength distribution
    cursor = db.conn.execute("""
        SELECT 
            CASE 
                WHEN relationship_strength >= 0.8 THEN 'very_strong (0.8-1.0)'
                WHEN relationship_strength >= 0.5 THEN 'strong (0.5-0.8)'
                WHEN relationship_strength >= 0.2 THEN 'medium (0.2-0.5)'
                ELSE 'weak (0.0-0.2)'
            END as strength_category,
            COUNT(*)
        FROM entities
        WHERE relationship_strength IS NOT NULL
        GROUP BY strength_category
        ORDER BY MIN(relationship_strength) DESC
    """)
    print("\n  Relationship Strength:")
    for category, count in cursor.fetchall():
        print(f"    • {category}: {count}")
    
    # With primary_identifier
    cursor = db.conn.execute("""
        SELECT COUNT(*) FROM entities WHERE primary_identifier IS NOT NULL
    """)
    with_identifier = cursor.fetchone()[0]
    print(f"\n  С primary_identifier: {with_identifier}/{len(entities)}")
    
    # With temporal data
    cursor = db.conn.execute("""
        SELECT COUNT(*) FROM entities WHERE first_seen IS NOT NULL
    """)
    with_temporal = cursor.fetchone()[0]
    print(f"  С temporal data: {with_temporal}/{len(entities)}")
    
    db.close()


if __name__ == "__main__":
    enrich_entities()

