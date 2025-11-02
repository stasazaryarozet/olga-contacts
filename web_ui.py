"""
Web UI для графа деловых контактов
Работает с PostgreSQL (Supabase) через Streamlit secrets
"""

import streamlit as st
import psycopg2
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Деловые Контакты — Ольга Розет",
    page_icon="🌐",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_db_connection():
    """Создать подключение к PostgreSQL или SQLite fallback."""
    # Try PostgreSQL first
    try:
        conn_url = st.secrets["connections"]["postgresql"]["url"]
        conn = psycopg2.connect(conn_url)
        st.sidebar.success("🟢 PostgreSQL (Supabase)")
        return conn, 'postgresql'
    except Exception as pg_error:
        # Fallback to SQLite
        try:
            import sqlite3
            conn = sqlite3.connect("data/contacts_v2.db", check_same_thread=False)
            st.sidebar.warning("🟡 SQLite (Local)")
            return conn, 'sqlite'
        except Exception as sqlite_error:
            st.error(f"❌ Не удалось подключиться ни к PostgreSQL, ни к SQLite")
            st.error(f"PostgreSQL: {pg_error}")
            st.error(f"SQLite: {sqlite_error}")
            st.stop()

conn, db_type = get_db_connection()

def execute_query(query, params=None):
    """Выполнить SQL запрос и вернуть результаты."""
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        if cur.description:  # SELECT query
            results = cur.fetchall()
            cur.close()
            return results
        else:  # UPDATE/INSERT query
            conn.commit()
            cur.close()
            return None
    except Exception as e:
        st.error(f"❌ Ошибка выполнения запроса: {e}")
        return []

# Sidebar
st.sidebar.title("🌐 Деловые Контакты")
st.sidebar.markdown("---")

scenario = st.sidebar.selectbox(
    "Выберите сценарий:",
    [
        "Q1: Топ контактов",
        "Q2: Остывшие контакты",
        "Q5: Самые связанные",
        "Q11: Кого представить?",
        "Обогащение: Tags & Notes"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Статистика:**")

# Stats
results = execute_query("SELECT COUNT(*) FROM entities WHERE type='Person'")
total_contacts = results[0][0] if results else 0

results = execute_query("SELECT COUNT(*) FROM edges")
total_edges = results[0][0] if results else 0

results = execute_query("SELECT status, COUNT(*) FROM entities GROUP BY status")
status_dist = dict(results) if results else {}

st.sidebar.metric("Всего контактов", total_contacts)
st.sidebar.metric("Связей", total_edges)

st.sidebar.markdown("**По status:**")
for status in ['active', 'cooling', 'cold', 'directory']:
    count = status_dist.get(status, 0)
    st.sidebar.markdown(f"- {status}: {count}")


# Main content
st.title("🌐 Граф Деловых Контактов")

if scenario == "Q1: Топ контактов":
    st.header("📊 Q1: Топ контактов по году")
    
    col1, col2, col3 = st.columns(3)
    
    # Get available years
    if db_type == 'postgresql':
        results = execute_query("""
            SELECT DISTINCT EXTRACT(YEAR FROM event_date::date) as year 
            FROM edges 
            WHERE event_date IS NOT NULL 
            ORDER BY year DESC
        """)
    else:  # sqlite
        results = execute_query("""
            SELECT DISTINCT substr(event_date, 1, 4) as year 
            FROM edges 
            WHERE event_date IS NOT NULL 
            ORDER BY year DESC
        """)
    available_years = [int(row[0]) for row in results] if results else []
    
    if not available_years:
        st.warning("⚠️ Нет данных о встречах.")
        st.stop()
    
    with col1:
        year = st.selectbox("Год:", available_years, index=0)
    
    with col2:
        top_n = st.slider("Топ:", 5, 50, 10)
    
    with col3:
        status_filter = st.multiselect(
            "Status:",
            ['active', 'cooling', 'cold', 'directory'],
            default=['active', 'cooling', 'cold']
        )
    
    # Debug info
    st.info(f"🔄 Параметры: Год={year}, Топ={top_n}, Status={', '.join(status_filter)}")
    
    if not status_filter:
        st.info("ℹ️ Выберите хотя бы один status")
        st.stop()
    
    if db_type == 'postgresql':
        query = """
            SELECT 
                e.label,
                e.status,
                e.relationship_strength,
                e.last_interaction,
                COUNT(DISTINCT ed.edge_id) as meeting_count
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                e.type = 'Person'
                AND ed.relation_type = 'co_attended'
                AND EXTRACT(YEAR FROM ed.event_date::date) = %s
                AND e.status = ANY(%s)
            GROUP BY e.entity_id, e.label, e.status, e.relationship_strength, e.last_interaction
            ORDER BY meeting_count DESC
            LIMIT %s
        """
        results = execute_query(query, (year, status_filter, top_n))
    else:  # sqlite
        placeholders = ','.join('?' * len(status_filter))
        query = f"""
            SELECT 
                e.label,
                e.status,
                e.relationship_strength,
                e.last_interaction,
                COUNT(DISTINCT ed.edge_id) as meeting_count
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                e.type = 'Person'
                AND ed.relation_type = 'co_attended'
                AND ed.event_date LIKE ?
                AND e.status IN ({placeholders})
            GROUP BY e.entity_id
            ORDER BY meeting_count DESC
            LIMIT ?
        """
        results = execute_query(query, (f"{year}%", *status_filter, top_n))
    
    if results:
        st.markdown(f"**Топ-{top_n} контактов в {year} году:**")
        
        for i, (label, status, strength, last_int, count) in enumerate(results, 1):
            with st.expander(f"{i}. {label} — {count} встреч"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Status", status)
                col2.metric("Strength", f"{strength:.3f}")
                col3.metric("Последний контакт", last_int or "N/A")
    else:
        st.info(f"ℹ️ Нет встреч в {year} году для выбранных status.")

elif scenario == "Q2: Остывшие контакты":
    st.header("❄️ Q2: Остывшие контакты")
    
    years_threshold = st.slider("Порог (лет без контакта):", 1, 5, 2)
    threshold_date = (datetime.now() - timedelta(days=years_threshold*365)).strftime("%Y-%m-%d")
    
    # Debug info to show reactivity
    st.info(f"🔄 Текущее значение порога: **{years_threshold} лет** → дата отсечки: {threshold_date}")
    
    if db_type == 'postgresql':
        query = """
            SELECT 
                e.label,
                e.status,
                e.relationship_strength,
                e.last_interaction,
                e.tags
            FROM entities e
            WHERE 
                e.type = 'Person'
                AND e.last_interaction IS NOT NULL
                AND e.last_interaction < %s
            ORDER BY e.last_interaction DESC
            LIMIT 50
        """
    else:  # sqlite
        query = """
            SELECT 
                e.label,
                e.status,
                e.relationship_strength,
                e.last_interaction,
                e.tags
            FROM entities e
            WHERE 
                e.type = 'Person'
                AND e.last_interaction IS NOT NULL
                AND e.last_interaction < ?
            ORDER BY e.last_interaction DESC
            LIMIT 50
        """
    
    results = execute_query(query, (threshold_date,))
    
    if results:
        st.markdown(f"**Контакты без взаимодействия > {years_threshold} лет:**")
        st.markdown(f"*Найдено: {len(results)}*")
        
        for label, status, strength, last_int, tags in results:
            with st.expander(f"{label} — последний контакт: {last_int}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Status", status)
                col2.metric("Strength", f"{strength:.3f}")
                col3.write(f"**Tags:** {tags or 'нет'}")
    else:
        st.success(f"✅ Нет контактов без взаимодействия > {years_threshold} лет")

elif scenario == "Q5: Самые связанные":
    st.header("🌟 Q5: Самые связанные контакты")
    
    col1, col2 = st.columns(2)
    
    with col1:
        top_n = st.slider("Топ:", 5, 50, 10)
    
    with col2:
        status_filter = st.multiselect(
            "Status:",
            ['active', 'cooling', 'cold', 'directory'],
            default=['active', 'directory']
        )
    
    # Debug info
    st.info(f"🔄 Параметры: Топ={top_n}, Status={', '.join(status_filter)}")
    
    if not status_filter:
        st.info("ℹ️ Выберите хотя бы один status")
        st.stop()
    
    if db_type == 'postgresql':
        query = """
            SELECT 
                e.label,
                e.status,
                e.relationship_strength,
                COUNT(DISTINCT ed.edge_id) as connection_count
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                e.type = 'Person'
                AND ed.relation_type = 'co_attended'
                AND e.status = ANY(%s)
            GROUP BY e.entity_id, e.label, e.status, e.relationship_strength
            ORDER BY connection_count DESC
            LIMIT %s
        """
        results = execute_query(query, (status_filter, top_n))
    else:  # sqlite
        placeholders = ','.join('?' * len(status_filter))
        query = f"""
            SELECT 
                e.label,
                e.status,
                e.relationship_strength,
                COUNT(DISTINCT ed.edge_id) as connection_count
            FROM entities e
            JOIN edges ed ON (ed.subject_id = e.entity_id OR ed.object_id = e.entity_id)
            WHERE 
                e.type = 'Person'
                AND ed.relation_type = 'co_attended'
                AND e.status IN ({placeholders})
            GROUP BY e.entity_id
            ORDER BY connection_count DESC
            LIMIT ?
        """
        results = execute_query(query, (*status_filter, top_n))
    
    if results:
        st.markdown(f"**Топ-{top_n} по количеству связей:**")
        
        for i, (label, status, strength, count) in enumerate(results, 1):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            col1.write(f"**{i}. {label}**")
            col2.metric("Связей", count)
            col3.metric("Strength", f"{strength:.3f}")
            col4.write(status)
    else:
        st.info("ℹ️ Нет данных для выбранных status.")

elif scenario == "Q11: Кого представить?":
    st.header("🤝 Q11: Кого представить контакту?")
    st.markdown("*Рекомендация на основе общих связей*")
    
    # Get all contacts
    results = execute_query("""
        SELECT label FROM entities 
        WHERE type='Person' AND status IN ('active', 'cooling', 'directory')
        ORDER BY label
    """)
    contacts = [row[0] for row in results] if results else []
    
    target_contact = st.selectbox("Выберите контакт:", contacts)
    
    if st.button("Найти рекомендации"):
        # Find target entity_id
        if db_type == 'postgresql':
            results = execute_query("SELECT entity_id FROM entities WHERE label = %s", (target_contact,))
        else:
            results = execute_query("SELECT entity_id FROM entities WHERE label = ?", (target_contact,))
        
        if not results:
            st.error("Контакт не найден")
            st.stop()
        target_id = results[0][0]
        
        # Find Olga's entity_id
        results = execute_query("""
            SELECT entity_id FROM identifiers 
            WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
            LIMIT 1
        """)
        
        if not results:
            st.error("Профиль Ольги не найден")
            st.stop()
        
        olga_id = results[0][0]
        
        # Find recommendations
        if db_type == 'postgresql':
            query = """
                WITH target_connections AS (
                    SELECT DISTINCT
                        CASE 
                            WHEN subject_id = %s THEN object_id
                            ELSE subject_id
                        END as connection_id
                    FROM edges
                    WHERE (subject_id = %s OR object_id = %s)
                    AND relation_type = 'co_attended'
                ),
                olga_connections AS (
                    SELECT DISTINCT
                        CASE 
                            WHEN subject_id = %s THEN object_id
                            ELSE subject_id
                        END as connection_id
                    FROM edges
                    WHERE (subject_id = %s OR object_id = %s)
                    AND relation_type = 'co_attended'
                )
                SELECT 
                    e.label,
                    e.relationship_strength,
                    e.status
                FROM olga_connections oc
                LEFT JOIN target_connections tc ON oc.connection_id = tc.connection_id
                JOIN entities e ON e.entity_id = oc.connection_id
                WHERE 
                    tc.connection_id IS NULL
                    AND e.type = 'Person'
                    AND e.entity_id != %s
                ORDER BY e.relationship_strength DESC
                LIMIT 10
            """
            results = execute_query(query, (
                target_id, target_id, target_id,
                olga_id, olga_id, olga_id,
                target_id
            ))
        else:  # sqlite
            # Simplified query for SQLite without CTEs
            query = """
                SELECT DISTINCT
                    e.label,
                    e.relationship_strength,
                    e.status
                FROM edges e1
                JOIN entities e ON (
                    (e1.subject_id = e.entity_id OR e1.object_id = e.entity_id)
                    AND e.type = 'Person'
                )
                WHERE 
                    (e1.subject_id = ? OR e1.object_id = ?)
                    AND e1.relation_type = 'co_attended'
                    AND e.entity_id NOT IN (
                        SELECT DISTINCT
                            CASE 
                                WHEN e2.subject_id = ? THEN e2.object_id
                                ELSE e2.subject_id
                            END
                        FROM edges e2
                        WHERE (e2.subject_id = ? OR e2.object_id = ?)
                        AND e2.relation_type = 'co_attended'
                    )
                    AND e.entity_id != ?
                ORDER BY e.relationship_strength DESC
                LIMIT 10
            """
            results = execute_query(query, (
                olga_id, olga_id,
                target_id, target_id, target_id,
                target_id
            ))
        
        if results:
            st.success(f"**Рекомендации для {target_contact}:**")
            
            for i, (label, strength, status) in enumerate(results, 1):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"**{i}. {label}**")
                col2.metric("Strength", f"{strength:.3f}")
                col3.write(status)
        else:
            st.info(f"{target_contact} уже знает всех ваших контактов!")

elif scenario == "Обогащение: Tags & Notes":
    st.header("✏️ Обогащение контактов")
    st.markdown("*Добавить tags и notes вручную*")
    
    # Get all contacts
    results = execute_query("""
        SELECT label FROM entities 
        WHERE type='Person'
        ORDER BY label
    """)
    contacts = [row[0] for row in results] if results else []
    
    if not contacts:
        st.warning("⚠️ Нет контактов в базе.")
        st.stop()
    
    selected_contact = st.selectbox("Выберите контакт:", contacts)
    
    # Get current data
    if db_type == 'postgresql':
        results = execute_query("""
            SELECT tags, notes, status, relationship_strength
            FROM entities WHERE label = %s
        """, (selected_contact,))
    else:
        results = execute_query("""
            SELECT tags, notes, status, relationship_strength
            FROM entities WHERE label = ?
        """, (selected_contact,))
    
    if results:
        current_tags, current_notes, status, strength = results[0]
        
        col1, col2 = st.columns(2)
        col1.metric("Status", status)
        col2.metric("Relationship Strength", f"{strength:.3f}")
        
        st.markdown("---")
        
        new_tags = st.text_input("Tags (через запятую):", value=current_tags or "")
        new_notes = st.text_area("Notes:", value=current_notes or "", height=150)
        
        if st.button("💾 Сохранить"):
            if db_type == 'postgresql':
                execute_query("""
                    UPDATE entities 
                    SET tags = %s, notes = %s, updated_at = %s
                    WHERE label = %s
                """, (new_tags, new_notes, datetime.now().isoformat(), selected_contact))
            else:
                execute_query("""
                    UPDATE entities 
                    SET tags = ?, notes = ?, updated_at = ?
                    WHERE label = ?
                """, (new_tags, new_notes, datetime.now().isoformat(), selected_contact))
            st.success(f"✅ Обновлено: {selected_contact}")
    else:
        st.error(f"❌ Контакт '{selected_contact}' не найден")


# Footer
st.markdown("---")
st.markdown("*Граф деловых контактов • v2.1 • PostgreSQL + Supabase • Budget: $0*")
