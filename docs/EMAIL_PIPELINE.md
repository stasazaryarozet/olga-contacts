# Инструкция: Email Pipeline

**Цель:** Автоматически извлечь деловые контакты и связи из Gmail

---

## Предварительная настройка (разово)

### 1. Создать App Password для Gmail

Gmail требует **App Password** (не обычный пароль) для доступа через IMAP.

**Шаги:**
1. Открыть https://myaccount.google.com/apppasswords
2. Войти в Google аккаунт Ольги
3. Выбрать "Mail" в Select app
4. Выбрать "Other" в Select device, ввести название: "Contact Builder"
5. Нажать **Generate**
6. Скопировать **16-символьный пароль** (например: `abcd efgh ijkl mnop`)

**Важно:** Этот пароль показывается **один раз**. Сохрани его.

### 2. Установить зависимости

```bash
cd contacts
source venv/bin/activate
pip install beautifulsoup4
```

---

## Запуск Email Pipeline

### Вариант 1: С паролем в команде (НЕ рекомендуется)

```bash
cd contacts
source venv/bin/activate

export GROQ_API_KEY="твой_ключ_groq"

python3 scripts/process_emails.py \
  --email olga.email@gmail.com \
  --password "abcd efgh ijkl mnop" \
  --since-days 30 \
  --limit 100
```

### Вариант 2: С паролем в переменной окружения (рекомендуется)

```bash
cd contacts
source venv/bin/activate

# Установить переменные окружения
export GROQ_API_KEY="твой_ключ_groq"
export GMAIL_PASSWORD="abcd efgh ijkl mnop"

# Запустить pipeline
python3 scripts/process_emails.py \
  --email olga.email@gmail.com \
  --since-days 30 \
  --limit 100
```

---

## Параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--email` | Gmail адрес (обязательно) | - |
| `--password` | App Password или через `GMAIL_PASSWORD` env var | - |
| `--folder` | IMAP папка | `INBOX` |
| `--since-days` | Обработать письма за последние N дней | `30` |
| `--limit` | Максимум писем для обработки | `100` |

---

## Что делает скрипт?

1. **Подключается к Gmail** через IMAP
2. **Скачивает письма** (последние 30 дней, до 100 писем)
3. **Извлекает текст** из писем (plain text или HTML → text)
4. **Отправляет в Groq** (Llama 3.3 70B) для извлечения:
   - Люди (Person)
   - Организации (Organization)
   - Связи (works_at, collaborated_with, etc.)
5. **Записывает в граф** (SQLite)

---

## Ожидаемое время

- **100 писем** ≈ 10-15 минут
- **Rate limiting:** 2 секунды между запросами (free tier)
- **Groq free tier:** 30 requests/minute

---

## После выполнения

Проверить результат:

```bash
cd contacts
python3 -c "
import sys
sys.path.insert(0, 'src')
from graph_db import GraphDB

db = GraphDB()
stats = db.get_stats()
print('\n📊 GRAPH STATS:')
for k, v in stats.items():
    print(f'  {k}: {v}')

# Show Olga's relations
rels = db.get_relations_for_person('Ольга Розет')
print(f'\n🔗 Ольга Розет: {len(rels)} relations')

# Show sample
if rels:
    print('\nSample relations:')
    for r in rels[:5]:
        print(f\"  - {r['relation_type']}: {r['target_name']}\")

db.close()
"
```

---

## Troubleshooting

### Ошибка: "Username and Password not accepted"
- Используй **App Password**, не обычный пароль Gmail
- Проверь, что 2FA включена в аккаунте (App Passwords требуют 2FA)

### Ошибка: "GROQ_API_KEY not set"
```bash
export GROQ_API_KEY="gsk_your_key_here"
```

### Слишком много писем
Уменьши `--limit`:
```bash
python3 scripts/process_emails.py --email olga@gmail.com --limit 50
```

---

## Следующие шаги

После Email Pipeline:
1. **Import Contacts** (`scripts/import_contacts.py`) — добавить структурированные контакты
2. **Google Search API** — расширить граф публичными источниками (snowballing)

**Ожидаемый результат:** Сотни узлов и связей из email переписки

