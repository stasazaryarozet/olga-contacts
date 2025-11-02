# ИНСТРУКЦИЯ: Создание Supabase проекта

Мне нужен доступ для завершения deployment.

## Вариант 1: Ты создаешь Supabase (3 минуты)

1. Перейди на https://supabase.com
2. Sign up с GitHub
3. Create new project:
   - Name: `olga-contacts`
   - Password: (сгенерируй сильный)
   - Region: West EU (London)
   - Plan: Free
4. После создания:
   - Project Settings → Database → Connection string (URI)
   - Скопируй полный URL

**Дай мне этот URL** — я:
- Запущу migration (schema + 6898 rows)
- Обновлю код для production
- Создам GitHub repo
- Deploy на Streamlit Cloud
- Настрою security

**Время:** 15 минут (всё автоматизировано)

---

## Вариант 2: Я создаю сам (requires credentials)

Для этого мне нужны:
- Твой GitHub account (для OAuth signup)
- Или: email + password для Supabase

После создания я выполню всё остальное автономно.

---

**Выбери вариант** или дай мне credentials для Варианта 2.

Без Supabase URL я не могу завершить deployment (ephemeral filesystem на Streamlit Cloud — Gemini confirmed).

