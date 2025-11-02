"""
Web UI MVP for Business Contacts Graph
Implements Top-5 scenarios based on Gemini recommendation (Variant B)

Streamlit app with:
- Q1: Top contacts by year (with status filter)
- Q2: Cold contacts
- Q5: Most connected
- Q11: Who to introduce X to?
- Manual enrichment (tags, notes)
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from enhanced_graph_db_universal import EnhancedGraphDB


# Page config
st.set_page_config(
    page_title="Деловые Контакты — Ольга Розет",
    page_icon="🌐",
    layout="wide"
)

# Initialize DB with PostgreSQL/SQLite auto-detection
@st.cache_resource
def get_db():
    """Get database connection (PostgreSQL from secrets or SQLite fallback)."""
    try:
        # Try Streamlit secrets (Production: Streamlit Cloud + Supabase)
        postgres_url = st.secrets["connections"]["postgresql"]["url"]
        return EnhancedGraphDB(postgres_url=postgres_url)
    except:
        # Fallback to SQLite (Local development)
        return EnhancedGraphDB(db_path="data/contacts_v2.db")

db = get_db()


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
cursor = db.conn.execute("SELECT COUNT(*) FROM entities WHERE type='Person'")
total_contacts = cursor.fetchone()[0]

cursor = db.conn.execute("SELECT COUNT(*) FROM edges")
total_edges = cursor.fetchone()[0]

cursor = db.conn.execute("SELECT status, COUNT(*) FROM entities GROUP BY status")
status_dist = dict(cursor.fetchall())

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
    
    try:
        col1, col2, col3 = st.columns(3)
        
        # Get available years from data
        cursor = db.conn.execute("""
            SELECT DISTINCT substr(event_date, 1, 4) as year 
            FROM edges 
            WHERE event_date IS NOT NULL 
            ORDER BY year DESC
        """)
        available_years = [int(row[0]) for row in cursor.fetchall()]
        
        if not available_years:
            st.warning("⚠️ Нет данных о встречах. Добавьте события через Calendar Pipeline.")
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
        
        if not status_filter:
            st.info("ℹ️ Выберите хотя бы один status")
            st.stop()
        
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
        
        cursor = db.conn.execute(query, (f"{year}%", *status_filter, top_n))
        results = cursor.fetchall()
        
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
    
    except Exception as e:
        st.error(f"❌ Ошибка при загрузке данных: {str(e)}")
        st.info("Попробуйте обновить страницу или обратитесь к администратору.")

elif scenario == "Q2: Остывшие контакты":
    st.header("❄️ Q2: Остывшие контакты")
    
    try:
        years_threshold = st.slider("Порог (лет без контакта):", 1, 5, 2)
        
        from datetime import timedelta
        threshold_date = (datetime.now() - timedelta(days=years_threshold*365)).strftime("%Y-%m-%d")
        
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
        
        cursor = db.conn.execute(query, (threshold_date,))
        results = cursor.fetchall()
        
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
    
    except Exception as e:
        st.error(f"❌ Ошибка при загрузке данных: {str(e)}")
        st.info("Попробуйте обновить страницу или обратитесь к администратору.")

elif scenario == "Q5: Самые связанные":
    st.header("🌟 Q5: Самые связанные контакты")
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            top_n = st.slider("Топ:", 5, 50, 10)
        
        with col2:
            status_filter = st.multiselect(
                "Status:",
                ['active', 'cooling', 'cold', 'directory'],
                default=['active', 'directory']
            )
        
        if not status_filter:
            st.info("ℹ️ Выберите хотя бы один status")
            st.stop()
        
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
        
        cursor = db.conn.execute(query, (*status_filter, top_n))
        results = cursor.fetchall()
        
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
    
    except Exception as e:
        st.error(f"❌ Ошибка при загрузке данных: {str(e)}")
        st.info("Попробуйте обновить страницу или обратитесь к администратору.")

elif scenario == "Q11: Кого представить?":
    st.header("🤝 Q11: Кого представить контакту?")
    
    st.markdown("*Рекомендация на основе общих связей*")
    
    try:
        # Get all active/cooling contacts
        cursor = db.conn.execute("""
            SELECT label FROM entities 
            WHERE type='Person' AND status IN ('active', 'cooling', 'directory')
            ORDER BY label
        """)
        contacts = [row[0] for row in cursor.fetchall()]
        
        target_contact = st.selectbox("Выберите контакт:", contacts)
        
        if st.button("Найти рекомендации"):
            # Find entity_id
            cursor = db.conn.execute("""
                SELECT entity_id FROM entities WHERE label = ?
            """, (target_contact,))
            target_id = cursor.fetchone()[0]
            
            # Find common neighbors with Olga
            cursor = db.conn.execute("""
                SELECT entity_id FROM identifiers 
                WHERE identifier LIKE '%olga%' OR identifier LIKE '%rozet%'
                LIMIT 1
            """)
            olga_result = cursor.fetchone()
            
            if olga_result:
                olga_id = olga_result[0]
                
                # Common neighbors query
                query = """
                    WITH target_connections AS (
                        SELECT DISTINCT
                            CASE 
                                WHEN subject_id = ? THEN object_id
                                ELSE subject_id
                            END as connection_id
                        FROM edges
                        WHERE (subject_id = ? OR object_id = ?)
                        AND relation_type = 'co_attended'
                    ),
                    olga_connections AS (
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
                        e.relationship_strength,
                        e.status
                    FROM olga_connections oc
                    LEFT JOIN target_connections tc ON oc.connection_id = tc.connection_id
                    JOIN entities e ON e.entity_id = oc.connection_id
                    WHERE 
                        tc.connection_id IS NULL
                        AND e.type = 'Person'
                        AND e.entity_id != ?
                    ORDER BY e.relationship_strength DESC
                    LIMIT 10
                """
                
                cursor = db.conn.execute(query, (
                    target_id, target_id, target_id,
                    olga_id, olga_id, olga_id,
                    target_id
                ))
                
                results = cursor.fetchall()
                
                if results:
                    st.success(f"**Рекомендации для {target_contact}:**")
                    
                    for i, (label, strength, status) in enumerate(results, 1):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.write(f"**{i}. {label}**")
                        col2.metric("Strength", f"{strength:.3f}")
                        col3.write(status)
                else:
                    st.info(f"{target_contact} уже знает всех ваших контактов!")
    
    except Exception as e:
        st.error(f"❌ Ошибка при загрузке данных: {str(e)}")
        st.info("Попробуйте обновить страницу или обратитесь к администратору.")

elif scenario == "Обогащение: Tags & Notes":
    st.header("✏️ Обогащение контактов")
    
    st.markdown("*Добавить tags и notes вручную*")
    
    try:
        # Get all contacts
        cursor = db.conn.execute("""
            SELECT label FROM entities 
            WHERE type='Person'
            ORDER BY label
        """)
        contacts = [row[0] for row in cursor.fetchall()]
        
        if not contacts:
            st.warning("⚠️ Нет контактов в базе. Импортируйте контакты через import_contacts.py")
            st.stop()
        
        selected_contact = st.selectbox("Выберите контакт:", contacts)
        
        # Get current data
        cursor = db.conn.execute("""
            SELECT tags, notes, status, relationship_strength
            FROM entities WHERE label = ?
        """, (selected_contact,))
        
        result = cursor.fetchone()
        if result:
            current_tags, current_notes, status, strength = result
            
            col1, col2 = st.columns(2)
            col1.metric("Status", status)
            col2.metric("Relationship Strength", f"{strength:.3f}")
            
            st.markdown("---")
            
            new_tags = st.text_input("Tags (через запятую):", value=current_tags or "")
            new_notes = st.text_area("Notes:", value=current_notes or "", height=150)
            
            if st.button("💾 Сохранить"):
                db.conn.execute("""
                    UPDATE entities 
                    SET tags = ?, notes = ?, updated_at = ?
                    WHERE label = ?
                """, (new_tags, new_notes, datetime.now().isoformat(), selected_contact))
                db.conn.commit()
                st.success(f"✅ Обновлено: {selected_contact}")
        else:
            st.error(f"❌ Контакт '{selected_contact}' не найден")
    
    except Exception as e:
        st.error(f"❌ Ошибка при обновлении данных: {str(e)}")
        st.info("Попробуйте обновить страницу или обратитесь к администратору.")


# Footer
st.markdown("---")
st.markdown("*Граф деловых контактов • v2.1 • Budget: $0*")

