"""
Fix Q1, Q5: Exclude Events (type='Event') from contact-based scenarios
Based on Gemini Q-DATA recommendation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from enhanced_graph_db import EnhancedGraphDB


def test_filters():
    """Test that Events are properly filtered from contact scenarios."""
    
    db = EnhancedGraphDB()
    
    print("🔍 Тест фильтрации Events из сценариев контактов")
    print()
    
    # Q1: Top contacts (BEFORE: with Events)
    print("❌ Q1 БЕЗ фильтра (неправильно):")
    cursor = db.conn.execute("""
        SELECT label, type, relationship_strength, status
        FROM entities
        WHERE relationship_strength > 0
        ORDER BY relationship_strength DESC
        LIMIT 10
    """)
    for i, (label, entity_type, strength, status) in enumerate(cursor.fetchall(), 1):
        marker = "⚠️" if entity_type == "Event" else "✓"
        print(f"  {i}. {marker} {label} ({entity_type}): {strength:.3f}")
    
    print()
    
    # Q1: Top contacts (AFTER: only Person)
    print("✅ Q1 С фильтром type='Person' (правильно):")
    cursor = db.conn.execute("""
        SELECT label, type, relationship_strength, status
        FROM entities
        WHERE relationship_strength > 0
        AND type = 'Person'
        ORDER BY relationship_strength DESC
        LIMIT 10
    """)
    for i, (label, entity_type, strength, status) in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. ✓ {label}: {strength:.3f} ({status})")
    
    print()
    
    # Q5: Most connected (with filter)
    print("✅ Q5 С фильтром type='Person':")
    cursor = db.conn.execute("""
        SELECT 
            e.label,
            COUNT(DISTINCT ed.edge_id) as connection_count,
            e.relationship_strength
        FROM entities e
        JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
        WHERE 
            ed.relation_type = 'co_attended'
            AND e.type = 'Person'
        GROUP BY e.entity_id
        ORDER BY connection_count DESC
        LIMIT 10
    """)
    for i, (label, count, strength) in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. ✓ {label}: {count} связей (strength: {strength:.3f})")
    
    print()
    
    # Statistics
    cursor = db.conn.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")
    print("📊 Статистика по type:")
    for entity_type, count in cursor.fetchall():
        print(f"  • {entity_type}: {count}")
    
    db.close()


if __name__ == "__main__":
    test_filters()

