# 🚀 QUICK START — SUPABASE IMPORT

## Один скрипт, 4 шага, 2 минуты

### Запуск

```bash
cd "Ольга/Дизайн-путешествия/contacts"
bash import_to_supabase.sh
```

### Что скрипт делает:

1. **Запрашивает connection string** (Session Pooler)
   - Ты вставляешь строку из Supabase UI
   - Формат: `postgresql://postgres.PROJECT:PASSWORD@...pooler.supabase.com:5432/postgres`

2. **Проверяет формат и подключение**
   - Валидирует, что это Session Pooler (`:5432`)
   - Тестирует подключение

3. **Импортирует данные**
   - Загружает `migration_data.sql` (6898 INSERT statements)
   - С unlimited timeout для больших запросов

4. **Проверяет результат**
   - Показывает count по всем таблицам
   - Expected: 464 entities, 5050 edges

---

## Где взять connection string?

### Вариант A: Dashboard → Database Settings
1. Открой Supabase Dashboard
2. Settings → Database
3. Секция "Connection pooling" → Session mode
4. Copy connection string

### Вариант B: Connect button (на главной проекта)
1. Нажми "Connect" (справа вверху)
2. Вкладка "Connection String"
3. Dropdown: "Session pooling"
4. Copy

---

## Что делать после импорта?

После успешного `import_to_supabase.sh`:

```bash
# Push код в GitHub
git add .
git commit -m "Production ready"
git remote add origin https://github.com/YOUR-USERNAME/olga-contacts.git
git push -u origin main

# Deploy на Streamlit Cloud
# → streamlit.io/cloud
# → New app → выбрать repo → добавить secrets → Deploy
```

Полная инструкция: `FINAL_DEPLOYMENT_STEPS.md` (Steps 4-6)

---

## Troubleshooting

**"Connection failed":**
- Проверь пароль (должен быть database password, не API key)
- Проверь, что выбрал Session mode (не Transaction)
- Проверь порт: должен быть `:5432`

**"Too many connections":**
- Supabase Free Tier: max 60 connections
- Закрой другие активные подключения
- Или повтори через 1-2 минуты

**"Import failed" на середине:**
- Скрипт остановится и покажет, какой INSERT упал
- Обычно это значит, что часть данных уже загружена
- Проверь через Step 4 (verify counts)

---

## Время выполнения

- Валидация: 5 сек
- Import: 60-120 сек (зависит от скорости интернета)
- Verify: 2 сек

**Total: ~2 минуты**

