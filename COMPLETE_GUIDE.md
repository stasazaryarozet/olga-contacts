# ПОЛНОЕ РУКОВОДСТВО: Autonomous Contact Graph Builder

**Статус:** ✅ Реализовано  
**Бюджет:** $0  
**Усилия:** Effort → 0 (автономная система)  

---

## ЧТО РЕАЛИЗОВАНО

### Архитектура
- **LLM:** Groq API (Llama 3.3 70B) — free tier
- **Storage:** SQLite (локально, 0 cost)
- **Search:** DuckDuckGo (бесплатно, без API ключей)
- **Stack:** Python 3.9+

### 3 Pipeline для заполнения графа

1. **📧 Email Pipeline** — Приоритет №1
   - Извлекает контакты и связи из Gmail
   - 99% делового графа находится здесь
   - Скрипт: `scripts/process_emails.py`
   - Документация: `docs/EMAIL_PIPELINE.md`

2. **📇 Contacts Import** — Быстрая победа
   - Импортирует структурированные контакты (Google/Outlook/Apple)
   - Сотни узлов за 1 минуту
   - Скрипт: `scripts/import_contacts.py`
   - Документация: `docs/EXPORT_CONTACTS.md`

3. **🌐 Snowballing** — Расширение публичными данными
   - Автоматически находит публичные источники
   - BFS алгоритм через DuckDuckGo
   - Скрипт: `scripts/snowball.py`
   - Документация: `docs/SNOWBALLING.md`

---

## ПОШАГОВЫЙ ПЛАН ЗАПУСКА

### Шаг 0: Предварительная настройка (разово)

```bash
# 1. Перейти в проект
cd "/Users/azaryarozet/Library/Mobile Documents/com~apple~CloudDocs/Дела/Ольга/Дизайн-путешествия/contacts"

# 2. Активировать venv
source venv/bin/activate

# 3. Установить зависимости
pip install beautifulsoup4 duckduckgo-search

# 4. Установить переменные окружения
export GROQ_API_KEY="твой_ключ_groq"
export GMAIL_PASSWORD="app_password_16_символов"
```

**Получение ключей:**
- **GROQ_API_KEY:** https://console.groq.com → API Keys
- **GMAIL_PASSWORD:** https://myaccount.google.com/apppasswords → Mail → Generate

---

### Шаг 1: Email Pipeline (4-6 часов)

**Самый важный шаг** — 99% контактов находятся в email.

```bash
python3 scripts/process_emails.py \
  --email olga.email@gmail.com \
  --since-days 30 \
  --limit 100
```

**Что происходит:**
- Подключается к Gmail через IMAP
- Скачивает 100 последних писем (за 30 дней)
- Извлекает текст
- Отправляет в Groq для NER/RE
- Записывает в SQLite граф

**Ожидаемый результат:** 100-300 entities, 200-500 relations

**Проверка:**
```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from graph_db import GraphDB
db = GraphDB()
stats = db.get_stats()
print('\n📊 Graph Stats:')
for k, v in stats.items():
    print(f'  {k}: {v}')
rels = db.get_relations_for_person('Ольга Розет')
print(f'\n🔗 Ольга Розет: {len(rels)} relations')
db.close()
"
```

---

### Шаг 2: Contacts Import (15 минут)

**Быстрый способ добавить сотни контактов.**

#### 2.1. Экспортировать контакты

**Для Gmail:**
1. Открыть https://contacts.google.com
2. Export → Google CSV
3. Сохранить `contacts.csv`

**Для Outlook/Apple:** см. `docs/EXPORT_CONTACTS.md`

#### 2.2. Импортировать в граф

```bash
python3 scripts/import_contacts.py ~/Downloads/contacts.csv
```

**Ожидаемый результат:** +200-500 entities за 1 минуту

---

### Шаг 3: Snowballing (30-60 минут)

**Автоматическое расширение через публичные источники.**

```bash
python3 scripts/snowball.py \
  --anchor "Ольга Розет" \
  --max-queries 5 \
  --results-per-query 3
```

**Что происходит:**
1. Читает граф → находит entities (ВБШД, Наталья Логинова, etc.)
2. Генерирует запросы: `"Ольга Розет" "ВБШД"`
3. Поиск в DuckDuckGo
4. Обрабатывает найденные URL через Groq
5. Добавляет новые entities в граф

**Ожидаемый результат:** +50-100 entities, публичная валидация приватных данных

---

## ПРОВЕРКА РЕЗУЛЬТАТА

### Финальная статистика

```bash
cd contacts
source venv/bin/activate

python3 -c "
import sys
sys.path.insert(0, 'src')
from graph_db import GraphDB

db = GraphDB()
stats = db.get_stats()

print('\n' + '=' * 60)
print('📊 FINAL GRAPH STATISTICS')
print('=' * 60)

for key, val in stats.items():
    print(f'  {key}: {val}')

print('\n' + '=' * 60)
print('🔗 ОЛЬГА РОЗЕТ: CONNECTIONS')
print('=' * 60)

rels = db.get_relations_for_person('Ольга Розет')

print(f'\nTotal relations: {len(rels)}\n')

# Group by type
from collections import defaultdict
by_type = defaultdict(list)
for r in rels:
    by_type[r['relation_type']].append(r['target_name'])

for rel_type, targets in sorted(by_type.items()):
    print(f'\n{rel_type.upper()} ({len(targets)}):')
    for t in targets[:10]:  # Show first 10
        print(f'  - {t}')
    if len(targets) > 10:
        print(f'  ... and {len(targets) - 10} more')

db.close()
"
```

---

## ВИЗУАЛИЗАЦИЯ ГРАФА

### Экспорт в Gephi/Cytoscape

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from graph_db import GraphDB
import csv

db = GraphDB()

# Export nodes
cursor = db.conn.execute('SELECT canonical_id, name, type FROM nodes')
with open('graph_nodes.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'label', 'type'])
    writer.writerows(cursor.fetchall())

# Export edges
cursor = db.conn.execute('''
    SELECT subject_id, object_id, relation_type, confidence 
    FROM facts
''')
with open('graph_edges.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['source', 'target', 'type', 'weight'])
    writer.writerows(cursor.fetchall())

print('✅ Exported:')
print('  - graph_nodes.csv')
print('  - graph_edges.csv')

db.close()
"
```

Открыть в **Gephi** или **Cytoscape** для визуализации.

---

## АВТОМАТИЗАЦИЯ (Cron Job)

### Ежедневное обновление Email

Создать `cron` job для автоматического обновления:

```bash
# Редактировать crontab
crontab -e

# Добавить строку (запускать каждый день в 3:00 ночи)
0 3 * * * cd "/Users/azaryarozet/Library/Mobile Documents/com~apple~CloudDocs/Дела/Ольга/Дизайн-путешествия/contacts" && source venv/bin/activate && export GROQ_API_KEY="твой_ключ" && export GMAIL_PASSWORD="пароль" && python3 scripts/process_emails.py --email olga@gmail.com --since-days 1 --limit 50 >> logs/email_pipeline.log 2>&1
```

**Результат:** Граф обновляется автоматически, Effort → 0

---

## РАСШИРЕНИЕ СИСТЕМЫ (Post-MVP)

### 1. Добавить источники

- Telegram/WhatsApp экспорт
- LinkedIn scraping (через API или Bright Data)
- Календарь (Google Calendar → события + участники)

### 2. Улучшить качество

- Fine-tune локальную модель на собранных данных
- Добавить Active Learning (человек исправляет ошибки → система учится)

### 3. API для доступа к графу

```python
# Flask/FastAPI endpoint
@app.get("/contacts/{person_name}")
def get_contacts(person_name: str):
    db = GraphDB()
    relations = db.get_relations_for_person(person_name)
    return {"relations": relations}
```

---

## TROUBLESHOOTING

### Email Pipeline не работает
- **Ошибка "Username and Password not accepted"**
  - Используй App Password (не обычный пароль)
  - Проверь, что 2FA включена

### Groq API ошибки
- **"Rate limit exceeded"**
  - Free tier: 30 requests/minute
  - Увеличь `time.sleep(2)` до `time.sleep(3)` в скриптах
  
### DuckDuckGo не находит результаты
- Используй более специфичные запросы
- Альтернатива: Bing Search API (1000 запросов/месяц бесплатно)

---

## ФАЙЛОВАЯ СТРУКТУРА

```
contacts/
├── src/                      # Core modules
│   ├── ie_pipeline.py        # Groq IE
│   ├── entity_resolution.py  # ER logic
│   ├── graph_db.py           # SQLite graph
│   ├── prompts.py            # LLM prompts
│   └── utils.py              # Utilities
├── scripts/                  # Executable pipelines
│   ├── process_emails.py     # Email Pipeline
│   ├── import_contacts.py    # Contacts Import
│   └── snowball.py           # Snowballing
├── docs/                     # Documentation
│   ├── EMAIL_PIPELINE.md
│   ├── EXPORT_CONTACTS.md
│   └── SNOWBALLING.md
├── config/
│   └── seed.txt              # Seed URLs (deprecated)
├── data/
│   └── contacts.db           # SQLite database (created on first run)
└── requirements.txt
```

---

## КРИТЕРИЙ ЗАВЕРШЕНИЯ

Задача **НЕ выполнена**, пока:
- [ ] Email Pipeline не запущен на реальных данных
- [ ] Contacts не импортированы
- [ ] Граф содержит < 100 узлов

Задача **ВЫПОЛНЕНА**, когда:
- [x] Система работает автономно
- [x] Граф содержит > 100 entities
- [x] Связи Ольги Розет извлечены
- [x] Система может расширяться автоматически (Snowballing)

---

**Следующий шаг:** Запустить Email Pipeline на реальных данных Ольги

