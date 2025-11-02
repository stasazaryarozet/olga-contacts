#!/usr/bin/env python3
"""
Temporal Analysis: Анализ динамики связей во времени
Отвечает на вопросы:
- С кем Ольга встречалась чаще всего в 2024?
- Какие контакты "остыли" (> 2 лет без встреч)?
- Как изменилась динамика проекта/связи?
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from graph_db import GraphDB
from utils import log


def analyze_top_contacts_by_year(db, person_name="Ольга Розет", year=2024, limit=20):
    """Топ контактов за год."""
    log(f"\n📊 Топ-{limit} контактов {person_name} в {year}:")
    
    cursor = db.conn.execute("""
        SELECT n.name, COUNT(*) as meetings
        FROM facts f
        JOIN nodes n ON f.object_id = n.canonical_id
        WHERE f.relation_type = 'co_attended'
          AND f.context LIKE ?
        GROUP BY n.name
        ORDER BY meetings DESC
        LIMIT ?
    """, (f'%{year}%', limit))
    
    results = cursor.fetchall()
    
    for i, (name, count) in enumerate(results, 1):
        log(f"  {i}. {name}: {count} встреч")
    
    return results


def analyze_cold_contacts(db, person_name="Ольга Розет", months_threshold=24):
    """Контакты без встреч более N месяцев."""
    log(f"\n❄️  'Остывшие' контакты (> {months_threshold} месяцев без встреч):")
    
    # Get all co_attended relations with dates
    cursor = db.conn.execute("""
        SELECT n.name, MAX(f.created_at) as last_meeting, f.context
        FROM facts f
        JOIN nodes n ON f.object_id = n.canonical_id
        WHERE f.relation_type = 'co_attended'
        GROUP BY n.name
        HAVING julianday('now') - julianday(last_meeting) > ?
        ORDER BY last_meeting DESC
        LIMIT 20
    """, (months_threshold * 30,))
    
    results = cursor.fetchall()
    
    if not results:
        log("  (Нет остывших контактов)")
        return []
    
    for name, last_meeting, context in results:
        # Parse date from context
        try:
            # Try to extract year from context
            import re
            year_match = re.search(r'20\d{2}', context or '')
            year = year_match.group() if year_match else 'N/A'
            log(f"  {name}: последняя встреча в {year}")
        except:
            log(f"  {name}: последняя встреча {last_meeting}")
    
    return results


def analyze_connection_strength(db, person1="Ольга Розет", person2=None, limit=10):
    """Сила связи между двумя людьми (количество совместных событий)."""
    if person2:
        log(f"\n🔗 Сила связи: {person1} ⟷ {person2}")
        
        # Find common events
        cursor = db.conn.execute("""
            SELECT e.name, f1.context
            FROM facts f1
            JOIN facts f2 ON f1.object_id = f2.object_id
            JOIN nodes e ON f1.object_id = e.canonical_id
            WHERE f1.relation_type = 'participated_in'
              AND f2.relation_type = 'participated_in'
              AND e.type = 'Event'
            LIMIT 20
        """)
        
        events = cursor.fetchall()
        log(f"  Совместных событий: {len(events)}")
        
        for event_name, context in events[:5]:
            log(f"    - {event_name}")
    
    else:
        log(f"\n🔗 Топ-{limit} самых сильных связей {person1}:")
        
        cursor = db.conn.execute("""
            SELECT n.name, COUNT(*) as strength
            FROM facts f
            JOIN nodes n ON f.object_id = n.canonical_id
            WHERE f.relation_type = 'co_attended'
            GROUP BY n.name
            ORDER BY strength DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        
        for i, (name, strength) in enumerate(results, 1):
            log(f"  {i}. {name}: {strength} совместных событий")
        
        return results


def analyze_project_dynamics(db, project_keyword):
    """Динамика проекта (частота встреч по событиям с ключевым словом)."""
    log(f"\n📈 Динамика проекта/темы: '{project_keyword}'")
    
    cursor = db.conn.execute("""
        SELECT e.name, f.context, COUNT(*) as participants
        FROM facts f
        JOIN nodes e ON f.object_id = e.canonical_id
        WHERE e.type = 'Event'
          AND (e.name LIKE ? OR f.context LIKE ?)
          AND f.relation_type = 'participated_in'
        GROUP BY e.name, f.context
        ORDER BY f.created_at DESC
        LIMIT 20
    """, (f'%{project_keyword}%', f'%{project_keyword}%'))
    
    results = cursor.fetchall()
    
    if not results:
        log(f"  Событий не найдено")
        return []
    
    log(f"  Найдено событий: {len(results)}")
    
    for event_name, context, participants in results[:10]:
        # Extract year from context
        import re
        year_match = re.search(r'20\d{2}', context or '')
        year = year_match.group() if year_match else 'N/A'
        log(f"    {year}: {event_name} ({participants} участников)")
    
    return results


def analyze_meeting_frequency_by_year(db):
    """Частота встреч по годам."""
    log(f"\n📅 Частота встреч по годам:")
    
    # Extract years from contexts
    cursor = db.conn.execute("""
        SELECT context FROM facts WHERE relation_type = 'co_attended'
    """)
    
    year_counts = defaultdict(int)
    
    import re
    for (context,) in cursor.fetchall():
        if context:
            year_matches = re.findall(r'20\d{2}', context)
            for year in year_matches:
                year_counts[year] += 1
    
    for year in sorted(year_counts.keys()):
        log(f"  {year}: {year_counts[year]} встреч")
    
    return year_counts


def generate_recommendations(db):
    """Генерация рекомендаций на основе анализа."""
    log(f"\n💡 РЕКОМЕНДАЦИИ:")
    
    # Cold contacts
    cold = analyze_cold_contacts(db, months_threshold=12)
    if len(cold) > 5:
        log(f"\n  ⚠️  У вас {len(cold)} контактов без встреч > 1 года")
        log(f"      Рекомендация: Написать им или организовать встречу")
    
    # Top contacts this year
    top_2024 = analyze_top_contacts_by_year(db, year=2024, limit=5)
    if top_2024:
        log(f"\n  ✅ Ваши ключевые контакты 2024:")
        for name, count in top_2024[:3]:
            log(f"      - {name} ({count} встреч)")


def main():
    """Main temporal analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Temporal Analysis of Contact Graph')
    parser.add_argument('--year', type=int, default=2024, help='Year to analyze')
    parser.add_argument('--top', type=int, default=20, help='Top N contacts')
    parser.add_argument('--project', type=str, help='Project/keyword to analyze')
    
    args = parser.parse_args()
    
    log("=" * 70)
    log("TEMPORAL ANALYSIS: Анализ динамики связей")
    log("=" * 70)
    
    db = GraphDB()
    
    # 1. Top contacts by year
    analyze_top_contacts_by_year(db, year=args.year, limit=args.top)
    
    # 2. Cold contacts
    analyze_cold_contacts(db, months_threshold=24)
    
    # 3. Connection strength
    analyze_connection_strength(db, limit=10)
    
    # 4. Meeting frequency by year
    analyze_meeting_frequency_by_year(db)
    
    # 5. Project dynamics (if specified)
    if args.project:
        analyze_project_dynamics(db, args.project)
    
    # 6. Recommendations
    generate_recommendations(db)
    
    log("\n" + "=" * 70)
    log("✅ Анализ завершён")
    log("=" * 70)
    
    db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

