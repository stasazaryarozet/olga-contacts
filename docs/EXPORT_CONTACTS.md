# Инструкции по экспорту контактов

**Цель:** Экспортировать контакты для импорта в граф

---

## Google Contacts (Gmail)

### Шаг 1: Экспорт
1. Открыть https://contacts.google.com
2. В левом меню нажать **"Export"** (Экспорт)
3. Выбрать формат: **"Google CSV"**
4. Нажать **"Export"**
5. Файл `contacts.csv` скачается

### Шаг 2: Импорт в граф
```bash
cd contacts
python3 scripts/import_contacts.py ~/Downloads/contacts.csv --format google
```

---

## Outlook

### Шаг 1: Экспорт
1. Открыть Outlook
2. File → Open & Export → Import/Export
3. Выбрать "Export to a file"
4. Выбрать "Comma Separated Values"
5. Выбрать папку "Contacts"
6. Сохранить как `outlook_contacts.csv`

### Шаг 2: Импорт в граф
```bash
cd contacts
python3 scripts/import_contacts.py outlook_contacts.csv --format outlook
```

---

## Apple Contacts (если есть доступ к macOS)

### Шаг 1: Экспорт
1. Открыть Contacts.app
2. Выбрать все контакты (⌘A)
3. File → Export → Export vCard
4. Сохранить как `contacts.vcf`

### Шаг 2: Импорт в граф
```bash
cd contacts
python3 scripts/import_contacts.py contacts.vcf
```

---

## iPhone (через iCloud)

### Шаг 1: Экспорт
1. На iPhone: Settings → [Your Name] → iCloud → включить Contacts
2. На компьютере: Открыть https://www.icloud.com
3. Войти с Apple ID
4. Открыть **Contacts**
5. Выбрать все контакты (Ctrl+A / ⌘A)
6. Настройки (⚙️) → Export vCard
7. Файл `contacts.vcf` скачается

### Шаг 2: Импорт в граф
```bash
cd contacts
python3 scripts/import_contacts.py ~/Downloads/contacts.vcf
```

---

## Android (через Google Contacts)

Используй инструкции для **Google Contacts** (выше)

---

## После импорта

Проверить результат:
```bash
cd contacts
python3 -c "
import sys
sys.path.insert(0, 'src')
from graph_db import GraphDB

db = GraphDB()
stats = db.get_stats()
print('\\n📊 GRAPH STATS:')
for k, v in stats.items():
    print(f'  {k}: {v}')

# Show Olga's relations
rels = db.get_relations_for_person('Ольга Розет')
print(f'\\n🔗 Ольга Розет: {len(rels)} relations')
db.close()
"
```

---

**Ожидаемый результат:** 100-300+ узлов в графе мгновенно

