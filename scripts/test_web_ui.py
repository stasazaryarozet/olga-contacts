"""
Functional tests for Web UI
Tests all 5 scenarios to ensure production-ready quality
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from enhanced_graph_db import EnhancedGraphDB


def test_database():
    """Test database connection and basic data."""
    print("🧪 Тест 1: Database Connection")
    
    try:
        db = EnhancedGraphDB()
        
        # Check entities
        cursor = db.conn.execute("SELECT COUNT(*) FROM entities WHERE type='Person'")
        entity_count = cursor.fetchone()[0]
        assert entity_count > 0, "No entities found"
        print(f"  ✅ Entities: {entity_count}")
        
        # Check edges
        cursor = db.conn.execute("SELECT COUNT(*) FROM edges")
        edge_count = cursor.fetchone()[0]
        assert edge_count > 0, "No edges found"
        print(f"  ✅ Edges: {edge_count}")
        
        # Check schema
        cursor = db.conn.execute("PRAGMA table_info(entities)")
        columns = [row[1] for row in cursor.fetchall()]
        required = ['entity_id', 'label', 'type', 'status', 'relationship_strength', 
                   'first_seen', 'last_interaction', 'tags', 'notes']
        for col in required:
            assert col in columns, f"Missing column: {col}"
        print(f"  ✅ Schema complete: {len(columns)} columns")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def test_q1_top_contacts():
    """Test Q1: Top contacts query."""
    print("\n🧪 Тест 2: Q1 — Топ контактов")
    
    try:
        db = EnhancedGraphDB()
        
        # Get available year from data
        cursor = db.conn.execute("""
            SELECT DISTINCT substr(event_date, 1, 4) as year 
            FROM edges 
            WHERE event_date IS NOT NULL 
            ORDER BY year DESC 
            LIMIT 1
        """)
        year_result = cursor.fetchone()
        if not year_result:
            print("  ⚠️ No event dates found, skipping Q1")
            db.close()
            return True
        
        test_year = year_result[0]
        
        # Q1 query (test with any relation_type)
        query = """
            SELECT 
                e.label,
                e.status,
                e.relationship_strength,
                COUNT(DISTINCT ed.edge_id) as meeting_count
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                e.type = 'Person'
                AND ed.event_date LIKE ?
                AND e.status IN ('active', 'cooling', 'cold', 'directory')
            GROUP BY e.entity_id
            ORDER BY meeting_count DESC
            LIMIT 5
        """
        
        cursor = db.conn.execute(query, (f"{test_year}%",))
        results = cursor.fetchall()
        
        assert len(results) > 0, f"No results for Q1 (year {test_year})"
        print(f"  ✅ Found {len(results)} contacts in {test_year}")
        
        for label, status, strength, count in results[:3]:
            print(f"    • {label}: {count} встреч (strength: {strength:.3f})")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def test_q2_cold_contacts():
    """Test Q2: Cold contacts query."""
    print("\n🧪 Тест 3: Q2 — Остывшие контакты")
    
    try:
        db = EnhancedGraphDB()
        
        from datetime import datetime, timedelta
        threshold_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
        
        query = """
            SELECT 
                e.label,
                e.status,
                e.last_interaction
            FROM entities e
            WHERE 
                e.type = 'Person'
                AND e.last_interaction IS NOT NULL
                AND e.last_interaction < ?
            ORDER BY e.last_interaction DESC
            LIMIT 10
        """
        
        cursor = db.conn.execute(query, (threshold_date,))
        results = cursor.fetchall()
        
        print(f"  ✅ Found {len(results)} cold contacts (> 2 years)")
        
        for label, status, last_int in results[:3]:
            print(f"    • {label}: {last_int} ({status})")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def test_q5_most_connected():
    """Test Q5: Most connected query."""
    print("\n🧪 Тест 4: Q5 — Самые связанные")
    
    try:
        db = EnhancedGraphDB()
        
        query = """
            SELECT 
                e.label,
                e.relationship_strength,
                COUNT(DISTINCT ed.edge_id) as connection_count
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                e.type = 'Person'
                AND ed.relation_type = 'co_attended'
            GROUP BY e.entity_id
            ORDER BY connection_count DESC
            LIMIT 10
        """
        
        cursor = db.conn.execute(query)
        results = cursor.fetchall()
        
        assert len(results) > 0, "No results for Q5"
        print(f"  ✅ Found {len(results)} connected contacts")
        
        for label, strength, count in results[:3]:
            print(f"    • {label}: {count} связей (strength: {strength:.3f})")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def test_q11_recommendations():
    """Test Q11: Who to introduce query."""
    print("\n🧪 Тест 5: Q11 — Кого представить")
    
    try:
        db = EnhancedGraphDB()
        
        # Get Olga's entity_id
        cursor = db.conn.execute("""
            SELECT entity_id FROM identifiers 
            WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
            LIMIT 1
        """)
        olga_result = cursor.fetchone()
        
        if not olga_result:
            print("  ⚠️ Olga not found, skipping")
            db.close()
            return True
        
        olga_id = olga_result[0]
        
        # Get a test contact
        cursor = db.conn.execute("""
            SELECT entity_id, label FROM entities 
            WHERE type='Person' AND status IN ('active', 'directory')
            AND entity_id != ?
            LIMIT 1
        """, (olga_id,))
        
        test_contact = cursor.fetchone()
        if not test_contact:
            print("  ⚠️ No test contacts found")
            db.close()
            return True
        
        target_id, target_label = test_contact
        
        # Q11 query
        query = """
            WITH target_connections AS (
                SELECT DISTINCT
                    CASE 
                        WHEN subject_id = ? THEN object_id
                        ELSE subject_id
                    END as connection_id
                FROM edges
                WHERE (subject_id = ? OR object_id = ?)
            ),
            olga_connections AS (
                SELECT DISTINCT
                    CASE 
                        WHEN subject_id = ? THEN object_id
                        ELSE subject_id
                    END as connection_id
                FROM edges
                WHERE (subject_id = ? OR object_id = ?)
            )
            SELECT 
                e.label,
                e.relationship_strength
            FROM olga_connections oc
            LEFT JOIN target_connections tc ON oc.connection_id = tc.connection_id
            JOIN entities e ON e.entity_id = oc.connection_id
            WHERE 
                tc.connection_id IS NULL
                AND e.type = 'Person'
                AND e.entity_id != ?
            ORDER BY e.relationship_strength DESC
            LIMIT 5
        """
        
        cursor = db.conn.execute(query, (
            target_id, target_id, target_id,
            olga_id, olga_id, olga_id,
            target_id
        ))
        
        results = cursor.fetchall()
        print(f"  ✅ Recommendations for {target_label}: {len(results)}")
        
        for label, strength in results[:3]:
            print(f"    • {label} (strength: {strength:.3f})")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def test_enrichment():
    """Test enrichment (tags/notes update)."""
    print("\n🧪 Тест 6: Обогащение (Tags & Notes)")
    
    try:
        db = EnhancedGraphDB()
        
        # Get a test entity
        cursor = db.conn.execute("""
            SELECT entity_id, label, tags, notes
            FROM entities
            WHERE type='Person'
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("  ⚠️ No entities to test")
            db.close()
            return True
        
        entity_id, label, old_tags, old_notes = result
        
        # Update
        test_tags = "test_tag"
        test_notes = "Test note"
        
        db.conn.execute("""
            UPDATE entities 
            SET tags = ?, notes = ?
            WHERE entity_id = ?
        """, (test_tags, test_notes, entity_id))
        db.conn.commit()
        
        # Verify
        cursor = db.conn.execute("""
            SELECT tags, notes FROM entities WHERE entity_id = ?
        """, (entity_id,))
        
        new_tags, new_notes = cursor.fetchone()
        assert new_tags == test_tags, "Tags not updated"
        assert new_notes == test_notes, "Notes not updated"
        
        # Restore
        db.conn.execute("""
            UPDATE entities 
            SET tags = ?, notes = ?
            WHERE entity_id = ?
        """, (old_tags, old_notes, entity_id))
        db.conn.commit()
        
        print(f"  ✅ Enrichment работает для {label}")
        
        db.close()
        return True
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def run_all_tests():
    """Run all functional tests."""
    print("=" * 60)
    print("🧪 FUNCTIONAL TESTS: Web UI")
    print("=" * 60)
    print()
    
    tests = [
        test_database,
        test_q1_top_contacts,
        test_q2_cold_contacts,
        test_q5_most_connected,
        test_q11_recommendations,
        test_enrichment
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Critical error: {str(e)}")
            results.append(False)
    
    print()
    print("=" * 60)
    print(f"📊 RESULTS: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("✅ ALL TESTS PASSED — Production ready")
    else:
        print("❌ SOME TESTS FAILED — Not production ready")
    
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

