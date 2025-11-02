"""
Fix critical issues in v2.1 schema based on Gemini feedback:
- Q-G1: Add 'directory', 'cooling' status
- Q-G2: Fix relationship_strength (exclude Olga, add recency)
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from enhanced_graph_db import EnhancedGraphDB


def fix_critical_issues():
    """Fix Q-G1 and Q-G2 based on Gemini recommendations."""
    
    print("🔧 Исправление критических проблем (Q-G1, Q-G2)")
    print()
    
    db = EnhancedGraphDB()
    
    # Get Olga's entity_id
    cursor = db.conn.execute("""
        SELECT entity_id FROM identifiers 
        WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
        LIMIT 1
    """)
    olga_result = cursor.fetchone()
    olga_id = olga_result[0] if olga_result else None
    
    print(f"  📌 Olga entity_id: {olga_id}")
    print()
    
    # Get max_degree (excluding Olga)
    cursor = db.conn.execute("""
        SELECT MAX(cnt) FROM (
            SELECT entity_id, COUNT(DISTINCT edge_id) as cnt
            FROM (
                SELECT subject_id as entity_id, edge_id FROM edges
                UNION ALL
                SELECT object_id as entity_id, edge_id FROM edges
            )
            WHERE entity_id != ?
            GROUP BY entity_id
        )
    """, (olga_id,))
    max_degree = cursor.fetchone()[0] or 1
    
    print(f"  📊 Max degree (excluding Olga): {max_degree}")
    print()
    
    # Get all entities
    cursor = db.conn.execute("SELECT entity_id FROM entities")
    entities = [row[0] for row in cursor.fetchall()]
    
    print(f"  🔄 Обновление {len(entities)} entities...")
    print()
    
    now = datetime.now()
    fixed = 0
    
    for entity_id in entities:
        # Get degree
        cursor = db.conn.execute("""
            SELECT COUNT(DISTINCT edge_id) FROM edges 
            WHERE (subject_id = ? OR object_id = ?)
        """, (entity_id, entity_id))
        degree = cursor.fetchone()[0]
        
        # Get last_interaction
        cursor = db.conn.execute("""
            SELECT MAX(event_date) FROM edges 
            WHERE (subject_id = ? OR object_id = ?)
        """, (entity_id, entity_id))
        last_interaction = cursor.fetchone()[0]
        
        # Fix Q-G1: Status
        if last_interaction:
            try:
                last_date = datetime.fromisoformat(last_interaction)
                days_since = (now - last_date).days
                
                if days_since <= 180:  # 6 months
                    status = 'active'
                elif days_since <= 730:  # 6 months - 2 years
                    status = 'cooling'
                else:  # > 2 years
                    status = 'cold'
            except:
                status = 'directory'
        else:
            # No interaction = from Contacts only
            status = 'directory'
        
        # Fix Q-G2: relationship_strength (weighted with recency)
        degree_norm = degree / max_degree if max_degree > 0 else 0.0
        
        if last_interaction:
            try:
                last_date = datetime.fromisoformat(last_interaction)
                days_since = (now - last_date).days
                # Recency: 0 days = 1.0, 365 days = 0.5, 730 days = 0.33
                recency_norm = 365.0 / (365.0 + days_since)
            except:
                recency_norm = 0.0
        else:
            recency_norm = 0.0
        
        # Weighted formula: 50% degree + 50% recency
        relationship_strength = round((0.5 * degree_norm) + (0.5 * recency_norm), 3)
        
        # Update
        db.conn.execute("""
            UPDATE entities SET
                status = ?,
                relationship_strength = ?,
                updated_at = ?
            WHERE entity_id = ?
        """, (status, relationship_strength, datetime.now().isoformat(), entity_id))
        
        fixed += 1
        if fixed % 50 == 0:
            db.conn.commit()
            print(f"  ✓ Исправлено {fixed}/{len(entities)}")
    
    db.conn.commit()
    
    print()
    print(f"✅ Исправлено: {fixed} entities")
    print()
    
    # Statistics
    print("📊 Новая статистика:")
    print()
    
    # Status distribution
    cursor = db.conn.execute("""
        SELECT status, COUNT(*) FROM entities 
        GROUP BY status 
        ORDER BY 
            CASE status
                WHEN 'active' THEN 1
                WHEN 'cooling' THEN 2
                WHEN 'cold' THEN 3
                WHEN 'directory' THEN 4
                ELSE 5
            END
    """)
    print("  Status:")
    for status, count in cursor.fetchall():
        print(f"    • {status}: {count}")
    
    print()
    
    # Top relationship_strength
    cursor = db.conn.execute("""
        SELECT label, relationship_strength, status
        FROM entities
        WHERE relationship_strength > 0
        ORDER BY relationship_strength DESC
        LIMIT 10
    """)
    print("  Топ-10 по relationship_strength (исправленный):")
    for label, strength, status in cursor.fetchall():
        print(f"    • {label}: {strength:.3f} ({status})")
    
    print()
    
    # Olga's strength
    if olga_id:
        cursor = db.conn.execute("""
            SELECT label, relationship_strength, status
            FROM entities WHERE entity_id = ?
        """, (olga_id,))
        olga_data = cursor.fetchone()
        if olga_data:
            print(f"  Olga: {olga_data[1]:.3f} ({olga_data[2]})")
    
    db.close()


if __name__ == "__main__":
    fix_critical_issues()

