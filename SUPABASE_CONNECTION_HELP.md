# 🔌 SUPABASE CONNECTION — ИНСТРУКЦИЯ

## Проблема
Прямое подключение к `db.lzwmoicxwrjgqmxfltcq.supabase.co:5432` не работает из-за IPv6.

## Решение: Session Pooler

### Шаг 1: Получить правильную connection string

1. Открой Supabase Dashboard → твой проект
2. Перейди в **Settings** → **Database** 
3. Найди секцию **"Connection pooling"** или кнопку **"Pooler settings"**
4. Выбери **"Session mode"** (НЕ Transaction mode)
5. Скопируй connection string

**Правильный формат:**
```
postgresql://postgres.lzwmoicxwrjgqmxfltcq:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```

**Критические параметры:**
- Username: `postgres.lzwmoicxwrjgqmxfltcq` (с точкой и project ID)
- Host: `aws-0-eu-central-1.pooler.supabase.com` (НЕ `db.lzwmoicxwrjgqmxfltcq`)
- Port: `5432` (для Session Pooler)
- Password: `NJtdpocY0oTbSZdI` (твой database password)

### Шаг 2: Проверь формат

Скопируй сюда полную строку (с реальным паролем), чтобы я мог её использовать.

Или если хочешь проверить сам:
- ✅ Должно быть: `postgres.lzwmoicxwrjgqmxfltcq` (с точкой)
- ❌ НЕ должно быть: `postgres:` (двоеточие без project ID)
- ✅ Host: `pooler.supabase.com`
- ❌ Host НЕ: `db.lzwmoicxwrjgqmxfltcq.supabase.co`
- ✅ Port: `:5432`

### Шаг 3: После получения строки

Я запущу скрипт импорта, который:
1. Подключится через Pooler (стабильное соединение)
2. Загрузит все 6898 INSERT statements из `migration_data.sql`
3. Проверит, что все 464 entities + 5050 edges загружены

---

## Альтернатива (если не найдёшь Pooler в UI)

В Supabase UI нажми на **"Connect"** (справа вверху) → вкладка **"Connection String"** → выбери **"Session pooling"**.

Скопируй то, что там показано.

