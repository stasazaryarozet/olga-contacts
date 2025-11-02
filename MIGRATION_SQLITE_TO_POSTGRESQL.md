# МИГРАЦИЯ: SQLite → PostgreSQL (Supabase)

**Дата:** 2025-11-01  
**Причина:** Streamlit Cloud использует ephemeral filesystem  
**Решение:** PostgreSQL (Supabase Free Tier)  
**Effort:** 1-2 часа  
**Budget:** $0

---

## Проблема

**Gemini подтвердил:**
> Гипотеза A (Ephemeral) — верна.
> 
> Streamlit Community Cloud использует ephemeral файловые системы.
> Локальный файл `contacts_v2.db` будет сброшен при каждом deployment/restart.
> 
> **Результат:** Все Tags и Notes будут потеряны. Нарушает UX (Effort → 0).

---

## Решение: PostgreSQL (Supabase Free Tier)

### ROI Analysis

| Вариант | Effort | Value | ROI | Вердикт |
|---------|--------|-------|-----|---------|
| Git LFS | Низкий | 0 | 0 | ❌ Не решает проблему записи |
| Google Drive Sync | Средний | Низкий | Низкий | ❌ Риск data corruption |
| **PostgreSQL (Supabase)** | **Средний** | **Критический** | **Очень высокий** | ✅ **Единственно верное** |

### Почему Supabase?

- ✅ **Budget:** $0 (generous free tier)
- ✅ **Persistent:** Настоящий stateful storage
- ✅ **Effort:** 1-2 часа на миграцию
- ✅ **UX:** Прозрачно для Ольги (0 изменений в workflow)
- ✅ **Production-ready:** Отделение app от database

---

## План миграции

### Шаг 1: Создать Supabase проект
1. Зарегистрироваться на [supabase.com](https://supabase.com)
2. Создать новый project
3. Получить connection string (PostgreSQL URL)

### Шаг 2: Конвертировать схему SQLite → PostgreSQL
5 таблиц:
- `entities`
- `identifiers`
- `edges`
- `sources`
- `raw_data`

Схемы почти идентичны (SQLite → PostgreSQL).

### Шаг 3: Миграция данных
- Экспорт из `contacts_v2.db` (464 entities, 5050 edges)
- Импорт в PostgreSQL

### Шаг 4: Обновить код
- `src/enhanced_graph_db.py`: `sqlite3.connect()` → `psycopg2.connect()`
- `web_ui.py`: Connection string из Streamlit Secrets
- `requirements.txt`: Добавить `psycopg2-binary`

### Шаг 5: Deployment
- Push to GitHub
- Deploy на Streamlit Cloud
- Добавить `SUPABASE_URL` в Streamlit Secrets

---

## Constraint-Driven Innovation (v6.2)

**Gemini:**
> Это тот же паттерн: ограничение (ephemeral filesystem) вынуждает принять **лучшее архитектурное решение** (отделение приложения от базы данных).

**До:**
- App + Database (SQLite) = монолит
- Ephemeral → data loss

**После:**
- App (Streamlit Cloud) + Database (Supabase) = distributed
- Persistent → production-ready
- Scalable для будущего

---

## Следующие действия

1. Создать Supabase account
2. Создать PostgreSQL schema
3. Миграция данных (SQLite → PostgreSQL)
4. Обновить `enhanced_graph_db.py`
5. Тестировать локально
6. Deploy на Streamlit Cloud

**Время:** 1-2 часа  
**Результат:** Production-ready deployment с persistent storage

