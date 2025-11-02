# DEPLOYMENT GUIDE: Streamlit Cloud + Supabase

**Дата:** 2025-11-01  
**Архитектура:** Streamlit Cloud (App) + Supabase (PostgreSQL Database)  
**Budget:** $0  
**Effort:** 1-2 часа

---

## 📋 Prerequisites

- ✅ GitHub account
- ✅ Данные экспортированы (6898 rows)
- ✅ Schema готова (`schema_postgresql.sql`)
- ✅ Migration ready (`migration_data.sql`)

---

## 🚀 Step 1: Создать Supabase проект

### 1.1. Регистрация
1. Перейти на [supabase.com](https://supabase.com)
2. Sign up (GitHub OAuth — fastest)
3. Confirm email

### 1.2. Создать проект
1. Click "New Project"
2. **Organization:** Personal (или создать новую)
3. **Project Name:** `olga-contacts`
4. **Database Password:** Сгенерировать (сохранить!)
5. **Region:** `West EU (London)` (ближайший к России)
6. **Pricing Plan:** **Free**
7. Click "Create new project"

⏱️ **Wait 2-3 minutes** для инициализации

---

## 🗄️ Step 2: Импорт схемы и данных

### 2.1. Открыть SQL Editor
1. В Supabase Dashboard → Left sidebar → **SQL Editor**
2. Click **New query**

### 2.2. Запустить Schema
1. Открыть файл `schema_postgresql.sql`
2. **Скопировать весь** содержимое
3. **Вставить** в SQL Editor
4. Click **Run** (или `Cmd+Enter`)

✅ **Ожидаемый результат:** 
```
Success. No rows returned
```

### 2.3. Запустить Migration Data
1. Открыть файл `migration_data.sql`
2. **Скопировать весь** содержимое (⚠️ это ~6898 INSERT statements)
3. **Вставить** в SQL Editor
4. Click **Run**

⏱️ **Wait 10-30 секунд**

✅ **Проверка:**
```sql
SELECT COUNT(*) FROM entities;
-- Expected: 464

SELECT COUNT(*) FROM edges;
-- Expected: 5050
```

---

## 🔑 Step 3: Получить Connection String

### 3.1. В Supabase Dashboard
1. Left sidebar → **Project Settings** (⚙️ иконка внизу)
2. **Database** (в меню слева)
3. Scroll down → **Connection string**
4. Tab: **URI** (не "Session pooler")

### 3.2. Скопировать URI
Format:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

⚠️ **Replace `[YOUR-PASSWORD]`** с паролем из Step 1.2

📋 **Сохранить** эту строку — она понадобится для Streamlit Secrets

---

## 📦 Step 4: Push to GitHub

### 4.1. Создать `.gitignore` (если нет)
```bash
cd "Ольга/Дизайн-путешествия/contacts"

# Добавить в .gitignore
echo "data/*.db" >> .gitignore
echo "migration_data.sql" >> .gitignore
echo ".env" >> .gitignore
echo "venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
```

### 4.2. Git init (если репо не существует)
```bash
git init
git add .
git commit -m "Initial commit: Production-ready web UI with PostgreSQL"
```

### 4.3. Create GitHub Repo
1. Перейти на [github.com/new](https://github.com/new)
2. **Repository name:** `olga-contacts`
3. **Privacy:** **Private** (для security)
4. **Don't** initialize with README (у нас уже есть)
5. Click **Create repository**

### 4.4. Push
```bash
git remote add origin https://github.com/[YOUR-USERNAME]/olga-contacts.git
git branch -M main
git push -u origin main
```

---

## 🌐 Step 5: Deploy на Streamlit Cloud

### 5.1. Создать Streamlit Cloud account
1. Перейти на [streamlit.io/cloud](https://streamlit.io/cloud)
2. Sign in with **GitHub**
3. Authorize Streamlit

### 5.2. Deploy App
1. Click **New app**
2. **Repository:** `[YOUR-USERNAME]/olga-contacts`
3. **Branch:** `main`
4. **Main file path:** `web_ui.py`
5. **App URL:** (custom subdomain, e.g., `olga-contacts`)
6. Click **Advanced settings...**

### 5.3. Добавить Secrets
В **Secrets** (TOML format):
```toml
[connections.postgresql]
url = "postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
```

⚠️ **Replace** с вашей connection string из Step 3

7. Click **Deploy!**

⏱️ **Wait 3-5 minutes** для первого deployment

---

## ✅ Step 6: Проверка

### 6.1. Открыть App URL
Example: `https://olga-contacts.streamlit.app`

### 6.2. Тест сценариев
1. **Q1: Топ контактов** — должен показать данные
2. **Q2: Остывшие контакты** — работает
3. **Q5: Самые связанные** — работает
4. **Q11: Кого представить** — работает
5. **Обогащение: Tags & Notes** — **КРИТИЧНО!** Добавить тег, обновить → reload страницу → тег должен **сохраниться**

✅ **Если тег сохранился** → Deployment успешен!

---

## 🔒 Step 7: Security (Basic Auth)

### 7.1. В Streamlit Cloud
1. App Dashboard → **Settings**
2. **Sharing** tab
3. **Viewer authentication:** Toggle ON
4. **Authentication method:** Streamlit authentication
5. **Allowed email addresses:** `o.g.rozet@gmail.com` (или другой email Ольги)
6. Click **Save**

✅ **Теперь** только Ольга может получить доступ (по email login)

---

## 📊 Architecture (Final)

```
┌─────────────────────────────────────────────────┐
│  Streamlit Cloud (Free)                         │
│  ┌──────────────────────────────────────────┐   │
│  │  web_ui.py                               │   │
│  │  - 5 Scenarios (Q1, Q2, Q5, Q11, Enrich)│   │
│  │  - Error handling (try/except)          │   │
│  │  - Basic auth (email)                   │   │
│  └──────────────────────────────────────────┘   │
│                    ▲                             │
│                    │ HTTPS                       │
│                    ▼                             │
│  ┌──────────────────────────────────────────┐   │
│  │  enhanced_graph_db.py                    │   │
│  │  - psycopg2.connect(SUPABASE_URL)       │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                     │
                     │ PostgreSQL Protocol
                     ▼
┌─────────────────────────────────────────────────┐
│  Supabase (Free Tier)                           │
│  ┌──────────────────────────────────────────┐   │
│  │  PostgreSQL Database                     │   │
│  │  - 464 entities                          │   │
│  │  - 5050 edges                            │   │
│  │  - Persistent storage                    │   │
│  │  - Auto-backups                          │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ **Budget:** $0 (both free tiers)
- ✅ **Persistent:** Tags/Notes сохраняются
- ✅ **Scalable:** Отделение app от database
- ✅ **Secure:** Private app + email auth
- ✅ **Accessible:** From anywhere (не localhost)
- ✅ **UX:** Effort → 0 (для Ольги)

---

## 🎯 Result

**Production-ready deployment** с:
- 6/6 tests passed
- Error handling в 5 сценариях
- Persistent PostgreSQL storage (Supabase)
- Secure access (Private + email auth)
- $0 budget

**URL:** `https://olga-contacts.streamlit.app` (или custom)

**Time to deploy:** 1-2 часа (от начала до конца)

---

## 📞 Support

Если что-то не работает:
1. Check Streamlit Cloud logs (App → Manage → Logs)
2. Check Supabase logs (Dashboard → Database → Logs)
3. Verify connection string в Streamlit Secrets
4. Verify PostgreSQL schema (tables exist?)

