#!/usr/bin/env python3
"""
Graph Query UI: Web-интерфейс для исследования графа контактов
Использует Streamlit для интерактивных запросов
"""

import sys
from pathlib import Path
import re
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def install_streamlit():
    """Install streamlit if not available."""
    try:
        import streamlit
    except ImportError:
        print("📦 Installing streamlit...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "pandas", "plotly"])


install_streamlit()

import streamlit as st
import pandas as pd
from graph_db import GraphDB


def get_top_contacts(db, year=None, limit=20):
    """Получить топ контактов за год."""
    if year:
        query = """
            SELECT n.name, COUNT(*) as meetings
            FROM facts f
            JOIN nodes n ON f.object_id = n.canonical_id
            WHERE f.relation_type = 'co_attended'
              AND f.context LIKE ?
            GROUP BY n.name
            ORDER BY meetings DESC
            LIMIT ?
        """
        cursor = db.conn.execute(query, (f'%{year}%', limit))
    else:
        query = """
            SELECT n.name, COUNT(*) as meetings
            FROM facts f
            JOIN nodes n ON f.object_id = n.canonical_id
            WHERE f.relation_type = 'co_attended'
            GROUP BY n.name
            ORDER BY meetings DESC
            LIMIT ?
        """
        cursor = db.conn.execute(query, (limit,))
    
    return cursor.fetchall()


def get_cold_contacts(db, months=12):
    """Получить контакты без встреч более N месяцев."""
    cursor = db.conn.execute("""
        SELECT n.name, f.context
        FROM facts f
        JOIN nodes n ON f.object_id = n.canonical_id
        WHERE f.relation_type = 'co_attended'
        GROUP BY n.name
        ORDER BY MAX(f.created_at) ASC
        LIMIT 20
    """)
    
    results = []
    for name, context in cursor.fetchall():
        # Extract year
        year_match = re.search(r'20\d{2}', context or '')
        year = year_match.group() if year_match else 'N/A'
        results.append((name, year))
    
    return results


def search_events(db, keyword):
    """Поиск событий по ключевому слову."""
    cursor = db.conn.execute("""
        SELECT e.name, COUNT(*) as participants, f.context
        FROM facts f
        JOIN nodes e ON f.object_id = e.canonical_id
        WHERE e.type = 'Event'
          AND (e.name LIKE ? OR f.context LIKE ?)
          AND f.relation_type = 'participated_in'
        GROUP BY e.name
        ORDER BY f.created_at DESC
        LIMIT 20
    """, (f'%{keyword}%', f'%{keyword}%'))
    
    return cursor.fetchall()


def get_event_participants(db, event_name):
    """Получить участников события."""
    cursor = db.conn.execute("""
        SELECT n.name
        FROM facts f
        JOIN nodes n ON f.subject_id = n.canonical_id
        JOIN nodes e ON f.object_id = e.canonical_id
        WHERE f.relation_type = 'participated_in'
          AND e.name = ?
          AND n.type = 'Person'
    """, (event_name,))
    
    return [row[0] for row in cursor.fetchall()]


def get_stats(db):
    """Получить общую статистику графа."""
    stats = db.get_stats()
    
    # Co-attended count
    cursor = db.conn.execute("SELECT COUNT(*) FROM facts WHERE relation_type = 'co_attended'")
    co_attended = cursor.fetchone()[0]
    
    # Years with data
    cursor = db.conn.execute("SELECT context FROM facts WHERE relation_type = 'co_attended' LIMIT 1000")
    years = set()
    for (context,) in cursor.fetchall():
        if context:
            year_matches = re.findall(r'20\d{2}', context)
            years.update(year_matches)
    
    return {
        **stats,
        'co_attended': co_attended,
        'years': sorted(years)
    }


def main():
    st.set_page_config(page_title="Граф Контактов Ольги Розет", layout="wide")
    
    st.title("🔗 Граф Контактов Ольги Розет")
    
    # Initialize DB
    db = GraphDB()
    
    # Sidebar with stats
    with st.sidebar:
        st.header("📊 Статистика")
        stats = get_stats(db)
        
        st.metric("Контактов (Person)", stats.get('Person', 0))
        st.metric("Событий (Event)", stats.get('Event', 0))
        st.metric("Связей (co_attended)", stats.get('co_attended', 0))
        
        if stats.get('years'):
            st.write(f"**Годы:** {', '.join(stats['years'])}")
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Топ контактов",
        "❄️ Остывшие контакты",
        "🔍 Поиск событий",
        "📈 Временная шкала"
    ])
    
    with tab1:
        st.header("Топ контактов")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            year = st.selectbox(
                "Год",
                ["Все время"] + (stats.get('years', []) or []),
                key="top_year"
            )
            limit = st.slider("Показать топ", 5, 50, 20)
        
        if st.button("Показать", key="top_btn"):
            year_filter = None if year == "Все время" else year
            results = get_top_contacts(db, year=year_filter, limit=limit)
            
            if results:
                df = pd.DataFrame(results, columns=['Контакт', 'Встреч'])
                
                st.dataframe(df, use_container_width=True)
                
                # Bar chart
                import plotly.express as px
                fig = px.bar(df.head(15), x='Встреч', y='Контакт', orientation='h',
                            title=f"Топ-15 контактов {year}")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Контакты не найдены")
    
    with tab2:
        st.header("Остывшие контакты")
        st.write("Контакты, с которыми давно не было встреч")
        
        months = st.slider("Период без встреч (месяцев)", 6, 36, 12)
        
        if st.button("Показать", key="cold_btn"):
            results = get_cold_contacts(db, months=months)
            
            if results:
                df = pd.DataFrame(results, columns=['Контакт', 'Последняя встреча (год)'])
                st.dataframe(df, use_container_width=True)
                
                st.info(f"💡 Рекомендация: Напишите этим людям или организуйте встречу")
            else:
                st.success("Остывших контактов нет!")
    
    with tab3:
        st.header("Поиск событий")
        
        keyword = st.text_input("Ключевое слово (название события, проект)", "Декорирование")
        
        if st.button("Найти", key="search_btn") or keyword:
            results = search_events(db, keyword)
            
            if results:
                st.write(f"Найдено событий: **{len(results)}**")
                
                for event_name, participants, context in results:
                    with st.expander(f"📅 {event_name} ({participants} участников)"):
                        # Extract year
                        year_match = re.search(r'20\d{2}', context or '')
                        year = year_match.group() if year_match else 'N/A'
                        
                        st.write(f"**Год:** {year}")
                        st.write(f"**Участников:** {participants}")
                        
                        # Get participants
                        people = get_event_participants(db, event_name)
                        if people:
                            st.write("**Участники:**")
                            for person in people[:10]:
                                st.write(f"- {person}")
                            if len(people) > 10:
                                st.write(f"_... и ещё {len(people) - 10}_")
            else:
                st.info("События не найдены")
    
    with tab4:
        st.header("Временная шкала")
        st.write("Распределение встреч по годам")
        
        # Get year distribution
        cursor = db.conn.execute("SELECT context FROM facts WHERE relation_type = 'co_attended'")
        year_counts = defaultdict(int)
        
        for (context,) in cursor.fetchall():
            if context:
                year_matches = re.findall(r'20\d{2}', context)
                for year in year_matches:
                    year_counts[year] += 1
        
        if year_counts:
            df = pd.DataFrame(
                sorted(year_counts.items()),
                columns=['Год', 'Встреч']
            )
            
            import plotly.express as px
            fig = px.line(df, x='Год', y='Встреч', markers=True,
                         title="Динамика встреч по годам")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Данных нет")
    
    db.close()


if __name__ == "__main__":
    main()

