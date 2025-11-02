"""Test v2 schema with business contact fields"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from enhanced_graph_db import EnhancedGraphDB


def test_v2():
    db = EnhancedGraphDB()
    
    print("📊 Тест v2 схемы (Деловые Контакты)")
    print()
    
    # 1. Check schema
    cursor = db.conn.execute("PRAGMA table_info(entities)")
    columns = [row[1] for row in cursor.fetchall()]
    
    print("✅ Поля entities:")
    for col in columns:
        print(f"  • {col}")
    
    print()
    
    # 2. Sample entities with new fields
    cursor = db.conn.execute("""
        SELECT 
            label, 
            status, 
            relationship_strength,
            last_interaction,
            primary_identifier
        FROM entities
        WHERE relationship_strength IS NOT NULL
        ORDER BY relationship_strength DESC
        LIMIT 10
    """)
    
    print("🌟 Топ-10 по relationship_strength:")
    for label, status, strength, last_int, primary_id in cursor.fetchall():
        print(f"  • {label}")
        print(f"    strength: {strength:.3f}, status: {status}")
        print(f"    last: {last_int or 'N/A'}")
        print()
    
    # 3. Status distribution
    cursor = db.conn.execute("""
        SELECT status, COUNT(*) FROM entities GROUP BY status
    """)
    
    print("📈 Status distribution:")
    for status, count in cursor.fetchall():
        print(f"  • {status}: {count}")
    
    db.close()


if __name__ == "__main__":
    test_v2()

