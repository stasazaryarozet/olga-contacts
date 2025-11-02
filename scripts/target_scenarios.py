"""
Target Scenarios: 10 questions to guide future development
Based on Gemini's recommendation (Step 5)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from enhanced_graph_db import EnhancedGraphDB


class GraphQueries:
    """10 target scenarios for the contact graph."""
    
    def __init__(self, db_path="data/contacts_enhanced.db"):
        self.db = EnhancedGraphDB(db_path)
    
    def q1_most_frequent_contacts(self, year: int = 2024, top: int = 10):
        """Q1: С кем я встречался чаще всего в [год]?"""
        
        query = """
            SELECT 
                e.label,
                COUNT(*) as meeting_count
            FROM edges ed
            JOIN entities e ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                ed.relation_type = 'co_attended'
                AND ed.event_date LIKE ?
                AND e.entity_id != (
                    SELECT entity_id FROM identifiers 
                    WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
                    LIMIT 1
                )
            GROUP BY e.entity_id
            ORDER BY meeting_count DESC
            LIMIT ?
        """
        
        cursor = self.db.conn.execute(query, (f"{year}%", top))
        
        print(f"📅 Q1: Топ-{top} контактов в {year} году:\n")
        
        for i, (label, count) in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. {label}: {count} встреч")
        
        print()
    
    def q2_cold_contacts(self, years_threshold: int = 2):
        """Q2: Какие контакты 'остыли' (нет встреч > N лет)?"""
        
        from datetime import datetime, timedelta
        threshold_date = (datetime.now() - timedelta(days=years_threshold*365)).strftime("%Y-%m-%d")
        
        query = """
            SELECT DISTINCT
                e.label,
                MAX(ed.event_date) as last_meeting
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                ed.relation_type = 'co_attended'
                AND e.entity_id != (
                    SELECT entity_id FROM identifiers 
                    WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
                    LIMIT 1
                )
            GROUP BY e.entity_id
            HAVING MAX(ed.event_date) < ?
            ORDER BY last_meeting DESC
            LIMIT 20
        """
        
        cursor = self.db.conn.execute(query, (threshold_date,))
        
        print(f"❄️  Q2: 'Остывшие' контакты (нет встреч > {years_threshold} лет):\n")
        
        for label, last_meeting in cursor.fetchall():
            print(f"  • {label} (последняя встреча: {last_meeting})")
        
        print()
    
    def q3_shortest_path(self, target_name: str):
        """Q3: Какой 'путь' до [целевого контакта]? (BFS)"""
        
        # Find target entity
        cursor = self.db.conn.execute("""
            SELECT entity_id FROM entities 
            WHERE label LIKE ? 
            LIMIT 1
        """, (f"%{target_name}%",))
        
        result = cursor.fetchone()
        if not result:
            print(f"❌ Контакт '{target_name}' не найден\n")
            return
        
        target_id = result[0]
        
        # Find Olga's entity
        cursor = self.db.conn.execute("""
            SELECT entity_id FROM identifiers 
            WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
            LIMIT 1
        """)
        
        olga_result = cursor.fetchone()
        if not olga_result:
            print("❌ Olga не найдена в базе\n")
            return
        
        olga_id = olga_result[0]
        
        # Simple BFS (depth 2 only for demo)
        query = """
            WITH direct_connections AS (
                SELECT DISTINCT
                    CASE 
                        WHEN subject_id = ? THEN object_id
                        ELSE subject_id
                    END as connection_id
                FROM edges
                WHERE (subject_id = ? OR object_id = ?)
                AND relation_type = 'co_attended'
            )
            SELECT 
                e.label,
                'DIRECT' as path_type
            FROM direct_connections dc
            JOIN entities e ON e.entity_id = dc.connection_id
            WHERE dc.connection_id = ?
            
            UNION
            
            SELECT 
                e2.label || ' (через ' || e1.label || ')' as label,
                'INDIRECT' as path_type
            FROM direct_connections dc1
            JOIN edges ed ON (ed.subject_id = dc1.connection_id OR ed.object_id = dc1.connection_id)
            JOIN entities e1 ON e1.entity_id = dc1.connection_id
            JOIN entities e2 ON (e2.entity_id = ed.subject_id OR e2.entity_id = ed.object_id)
            WHERE 
                e2.entity_id = ?
                AND ed.relation_type = 'co_attended'
            LIMIT 1
        """
        
        cursor = self.db.conn.execute(query, (olga_id, olga_id, olga_id, target_id, target_id))
        
        print(f"🔍 Q3: Путь до '{target_name}':\n")
        
        results = cursor.fetchall()
        if results:
            for label, path_type in results:
                print(f"  → {label}")
        else:
            print(f"  ❌ Путь не найден")
        
        print()
    
    def q4_common_neighbors(self, person1: str, person2: str):
        """Q4: Кто знает и [X], и [Y]?"""
        
        query = """
            WITH person1_connections AS (
                SELECT DISTINCT
                    CASE 
                        WHEN subject_id = (SELECT entity_id FROM entities WHERE label LIKE ? LIMIT 1) 
                        THEN object_id
                        ELSE subject_id
                    END as connection_id
                FROM edges
                WHERE (
                    subject_id = (SELECT entity_id FROM entities WHERE label LIKE ? LIMIT 1)
                    OR object_id = (SELECT entity_id FROM entities WHERE label LIKE ? LIMIT 1)
                )
                AND relation_type = 'co_attended'
            ),
            person2_connections AS (
                SELECT DISTINCT
                    CASE 
                        WHEN subject_id = (SELECT entity_id FROM entities WHERE label LIKE ? LIMIT 1) 
                        THEN object_id
                        ELSE subject_id
                    END as connection_id
                FROM edges
                WHERE (
                    subject_id = (SELECT entity_id FROM entities WHERE label LIKE ? LIMIT 1)
                    OR object_id = (SELECT entity_id FROM entities WHERE label LIKE ? LIMIT 1)
                )
                AND relation_type = 'co_attended'
            )
            SELECT e.label
            FROM person1_connections p1
            JOIN person2_connections p2 ON p1.connection_id = p2.connection_id
            JOIN entities e ON e.entity_id = p1.connection_id
            LIMIT 20
        """
        
        cursor = self.db.conn.execute(query, (
            f"%{person1}%", f"%{person1}%", f"%{person1}%",
            f"%{person2}%", f"%{person2}%", f"%{person2}%"
        ))
        
        print(f"🔗 Q4: Общие контакты '{person1}' и '{person2}':\n")
        
        results = cursor.fetchall()
        if results:
            for (label,) in results:
                print(f"  • {label}")
        else:
            print(f"  ❌ Общих контактов не найдено")
        
        print()
    
    def q5_most_connected(self, top: int = 10):
        """Q5: Кто самый 'связанный' контакт? (degree centrality)"""
        
        query = """
            SELECT 
                e.label,
                COUNT(DISTINCT ed.edge_id) as connection_count
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                ed.relation_type = 'co_attended'
                AND e.entity_id != (
                    SELECT entity_id FROM identifiers 
                    WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
                    LIMIT 1
                )
            GROUP BY e.entity_id
            ORDER BY connection_count DESC
            LIMIT ?
        """
        
        cursor = self.db.conn.execute(query, (top,))
        
        print(f"🌟 Q5: Топ-{top} самых связанных контактов:\n")
        
        for i, (label, count) in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. {label}: {count} связей")
        
        print()
    
    def q6_activity_by_month(self, year: int = 2024):
        """Q6: Динамика активности по месяцам в [год]?"""
        
        query = """
            SELECT 
                substr(event_date, 1, 7) as month,
                COUNT(*) as event_count
            FROM edges
            WHERE 
                relation_type = 'co_attended'
                AND event_date LIKE ?
            GROUP BY month
            ORDER BY month
        """
        
        cursor = self.db.conn.execute(query, (f"{year}%",))
        
        print(f"📈 Q6: Активность встреч в {year} году:\n")
        
        for month, count in cursor.fetchall():
            print(f"  {month}: {'█' * count} ({count})")
        
        print()
    
    def q7_organizations(self):
        """Q7: Какие организации в графе?"""
        
        query = """
            SELECT 
                e.label,
                COUNT(DISTINCT ed.subject_id) as member_count
            FROM entities e
            JOIN edges ed ON ed.object_id = e.entity_id
            WHERE 
                ed.relation_type IN ('works_at', 'affiliated_with')
            GROUP BY e.entity_id
            ORDER BY member_count DESC
        """
        
        cursor = self.db.conn.execute(query)
        
        print(f"🏢 Q7: Организации в графе:\n")
        
        results = cursor.fetchall()
        if results:
            for label, count in results:
                print(f"  • {label} ({count} человек)")
        else:
            print(f"  ℹ️  Организации не найдены (добавьте через LinkedIn/Email)")
        
        print()
    
    def q8_cluster_detection(self):
        """Q8: Есть ли 'кластеры' (группы тесно связанных контактов)?"""
        
        # Simplified: top groups by shared events
        query = """
            SELECT 
                GROUP_CONCAT(DISTINCT e.label) as group_members,
                COUNT(DISTINCT ed.source_id) as shared_events
            FROM edges ed
            JOIN entities e ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE ed.relation_type = 'co_attended'
            GROUP BY ed.source_id
            HAVING COUNT(DISTINCT e.entity_id) >= 3
            ORDER BY shared_events DESC
            LIMIT 5
        """
        
        cursor = self.db.conn.execute(query)
        
        print(f"🎯 Q8: Кластеры (группы с общими встречами):\n")
        
        for group, count in cursor.fetchall():
            members = group.split(',')[:5]  # Show first 5
            print(f"  • {', '.join(members)}... ({count} общих встреч)")
        
        print()
    
    def q9_new_vs_old(self, year: int = 2024):
        """Q9: Новые vs старые контакты в [год]?"""
        
        query = """
            WITH first_meetings AS (
                SELECT 
                    e.entity_id,
                    e.label,
                    MIN(ed.event_date) as first_meeting
                FROM entities e
                JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
                WHERE ed.relation_type = 'co_attended'
                GROUP BY e.entity_id
            )
            SELECT 
                CASE 
                    WHEN first_meeting LIKE ? THEN 'NEW'
                    ELSE 'OLD'
                END as contact_type,
                COUNT(*) as count
            FROM first_meetings
            GROUP BY contact_type
        """
        
        cursor = self.db.conn.execute(query, (f"{year}%",))
        
        print(f"🆕 Q9: Новые vs старые контакты в {year}:\n")
        
        for contact_type, count in cursor.fetchall():
            emoji = "🆕" if contact_type == "NEW" else "👥"
            print(f"  {emoji} {contact_type}: {count}")
        
        print()
    
    def q10_all_identifiers(self, person_name: str):
        """Q10: Все идентификаторы для [контакта]? (Entity Resolution demo)"""
        
        query = """
            SELECT 
                i.identifier,
                i.identifier_type
            FROM identifiers i
            JOIN entities e ON e.entity_id = i.entity_id
            WHERE e.label LIKE ?
        """
        
        cursor = self.db.conn.execute(query, (f"%{person_name}%",))
        
        print(f"🔑 Q10: Все идентификаторы '{person_name}':\n")
        
        results = cursor.fetchall()
        if results:
            for identifier, id_type in results:
                print(f"  • {identifier} ({id_type})")
        else:
            print(f"  ❌ Контакт не найден")
        
        print()
    
    def run_all(self):
        """Run all 10 queries."""
        
        print("=" * 60)
        print("10 ЦЕЛЕВЫХ СЦЕНАРИЕВ: Вопросы к графу")
        print("=" * 60)
        print()
        
        self.q1_most_frequent_contacts(year=2024, top=10)
        self.q2_cold_contacts(years_threshold=2)
        # self.q3_shortest_path("Наталья")  # Uncomment with real name
        # self.q4_common_neighbors("Olga", "Наталья")  # Uncomment with real names
        self.q5_most_connected(top=10)
        self.q6_activity_by_month(year=2024)
        self.q7_organizations()
        self.q8_cluster_detection()
        self.q9_new_vs_old(year=2024)
        # self.q10_all_identifiers("Olga")  # Uncomment with real name
        
        print("=" * 60)
        
        self.db.close()


if __name__ == "__main__":
    queries = GraphQueries()
    queries.run_all()

