# ✅ DEPLOYMENT — ФИНАЛЬНЫЕ ШАГИ (5 минут)

**Текущий статус:**
- ✅ Supabase project создан
- ✅ Schema частично импортирована (entities, identifiers, edges, raw_data)
- ⏸️ Осталось: исправить sources table и импортировать данные

---

## Шаг 1: Исправить sources schema (30 сек)

В **SQL Editor** Supabase выполни:

```sql
-- Fix sources table (with CASCADE to handle foreign keys)
DROP TABLE IF EXISTS sources CASCADE;

CREATE TABLE sources (
    source_id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    source_type TEXT,
    hash TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recreate foreign key constraints
ALTER TABLE edges 
ADD CONSTRAINT edges_source_id_fkey 
FOREIGN KEY (source_id) REFERENCES sources(source_id);

ALTER TABLE raw_data 
ADD CONSTRAINT raw_data_source_id_fkey 
FOREIGN KEY (source_id) REFERENCES sources(source_id);
```

Click **RUN**

---

## Шаг 2: Импорт данных (2 минуты)

**Файл:** `migration_data.sql` (1.2MB, 6898 INSERT statements)

### Option A: Полный импорт (если SQL Editor справится)

1. Открой `migration_data.sql` в текстовом редакторе
2. Скопируй **весь файл**
3. Вставь в SQL Editor
4. Click **RUN** (может занять 30-60 сек)

### Option B: Батчами (если Option A не работает)

Разбей файл на части:

```bash
cd "Ольга/Дизайн-путешествия/contacts"

# Split на батчи по 1000 строк
split -l 1000 migration_data.sql batch_

# Получишь batch_aa, batch_ab, batch_ac, etc.
```

Вставляй каждый batch по очереди в SQL Editor.

---

## Шаг 3: Проверка (30 сек)

В SQL Editor:

```sql
-- Verify data
SELECT 
    (SELECT COUNT(*) FROM entities) as entities,
    (SELECT COUNT(*) FROM edges) as edges,
    (SELECT COUNT(*) FROM sources) as sources,
    (SELECT COUNT(*) FROM identifiers) as identifiers;
```

**Expected:**
- entities: 464
- edges: 5050
- sources: 460
- identifiers: 464

---

## Шаг 4: GitHub Push (1 минута)

```bash
cd "Ольга/Дизайн-путешествия/contacts"

# Add to git
git add .
git commit -m "Production ready: PostgreSQL + Streamlit Cloud"

# Create GitHub repo (if not exists)
# Go to github.com/new → create "olga-contacts" (Private)

git remote add origin https://github.com/YOUR-USERNAME/olga-contacts.git
git branch -M main
git push -u origin main
```

---

## Шаг 5: Streamlit Cloud Deploy (2 минуты)

1. https://streamlit.io/cloud → Sign in with GitHub
2. **New app**:
   - Repository: `YOUR-USERNAME/olga-contacts`
   - Branch: `main`
   - Main file: `web_ui.py`
   - App URL: `olga-contacts`

3. **Advanced settings** → **Secrets**:
```toml
[connections.postgresql]
url = "postgresql://postgres:NJtdpocY0oTbSZdI@db.lzwmoicxwrjgqmxfltcq.supabase.co:5432/postgres"
```

4. **Deploy!** (wait 3-5 min)

---

## Шаг 6: Security (30 сек)

Streamlit App → **Settings** → **Sharing**:
- Viewer authentication: **ON**
- Allowed emails: `o.g.rozet@gmail.com`
- **Save**

---

## ✅ ГОТОВО!

**URL:** `https://olga-contacts.streamlit.app`

Отправь Ольге!

---

## Troubleshooting

**"Error connecting to database":**
- Check Supabase: Tables есть? Data есть?
- Check Streamlit Secrets: connection string правильный?

**"No data showing":**
- Verify в SQL Editor: `SELECT COUNT(*) FROM entities;`

---

**Total time:** ~5 минут активных действий
**Result:** Production-ready URL с 464 entities, 5050 edges
