# РАСШИРЕННАЯ СХЕМА ENTITIES: Деловые контакты

**Дата:** 2025-11-01, 24:25  
**Источник:** Gemini recommendation (на основе GIGO принципа)  
**Критичность:** Высокая (до Web UI)

---

## Проблема: Минимальная схема

### Текущая схема (недостаточна):
```sql
entities (
    entity_id INTEGER PRIMARY KEY,
    label TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'Person', 'Organization'
    metadata TEXT,       -- JSON (неструктурированный)
    created_at TEXT
)
```

**Ограничения:**
- ❌ Нет `status` (active, cold, target)
- ❌ Нет `domain` (design, tech, academic, media)
- ❌ Нет `relationship_strength` (calculated)
- ❌ Нет `primary_identifier` (canonical email)
- ❌ Нет `last_interaction` (для Q2 "cold contacts")
- ❌ Нет `first_seen` (для Q9 "new vs old")
- ❌ Нет `notes` (ручные заметки пользователя)

---

## Решение: Расширенная схема

### Новая схема (для любых деловых контактов):

```sql
entities (
    -- Identity
    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,                    -- Human-readable name
    type TEXT NOT NULL,                     -- 'Person', 'Organization', 'Event'
    primary_identifier TEXT,                -- Canonical identifier (email)
    
    -- Business Contact Fields (для любых деловых связей)
    status TEXT DEFAULT 'unknown',          -- 'active', 'cold', 'target', 'archived', 'unknown'
    domain TEXT,                            -- 'design', 'tech', 'academic', 'media', 'other'
    relationship_strength REAL,             -- 0.0-1.0 (calculated from Q5, Q1)
    
    -- Temporal
    first_seen TEXT,                        -- ISO date (первое появление в данных)
    last_interaction TEXT,                  -- ISO date (последнее событие/email)
    
    -- User-Enriched
    notes TEXT,                             -- Ручные заметки пользователя
    tags TEXT,                              -- Comma-separated tags
    
    -- System
    metadata TEXT,                          -- JSON (дополнительные данные)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

---

## Семантика полей

### 1. Identity (базовая идентификация)

#### `entity_id`
- **Type:** INTEGER PRIMARY KEY
- **Смысл:** Канонический ID (immutable)
- **Источник:** Auto-increment

#### `label`
- **Type:** TEXT NOT NULL
- **Смысл:** Human-readable имя
- **Примеры:** "Olga Rozet", "ВБШД", "Paris Design Week 2024"

#### `type`
- **Type:** TEXT NOT NULL
- **Значения:** 'Person', 'Organization', 'Event'
- **Смысл:** Тип сущности

#### `primary_identifier`
- **Type:** TEXT (nullable)
- **Смысл:** Канонический идентификатор (обычно email для Person)
- **Примеры:** "o.g.rozet@gmail.com", "info@vbshd.ru"
- **GIGO:** Помогает избежать дубликатов при ручном вводе

---

### 2. Business Contact Fields (для любых деловых связей)

#### `status`
- **Type:** TEXT
- **Значения:**
  - `'active'` — регулярное взаимодействие (< 6 месяцев)
  - `'cold'` — нет взаимодействия > 6 месяцев (Q2)
  - `'target'` — потенциальный контакт (еще нет взаимодействия)
  - `'archived'` — больше не актуален
  - `'unknown'` — default (не определён)
- **Вычисление:**
  ```python
  if last_interaction > now() - 6 months: status = 'active'
  elif last_interaction < now() - 2 years: status = 'cold'
  ```
- **Использование:** Фильтрация в Web UI, Q2 (Cold Contacts)
- **Примеры:** Партнёр (active), бывший коллега (cold), потенциальный контакт (target)

#### `domain`
- **Type:** TEXT (nullable)
- **Значения:**
  - `'design'` — дизайн, архитектура
  - `'tech'` — технологии, IT
  - `'academic'` — университеты, научные институты
  - `'media'` — журналисты, издательства
  - `'business'` — общий бизнес
  - `'art'` — искусство, музеи
  - `'government'` — государственные учреждения
  - `'other'` — не определено
- **Источник:** Может извлекаться из:
  - LinkedIn (Organization → domain)
  - Email (domain анализ, e.g., "@vbshd.ru" → 'design')
  - Manual (ручной ввод через Web UI)
- **Использование:** Сегментация контактов, фильтрация
- **Примеры:** Куратор (design), профессор (academic), журналист (media), партнёр (business)

#### `relationship_strength`
- **Type:** REAL (0.0 - 1.0)
- **Смысл:** Сила связи с Ольгой
- **Вычисление:**
  ```python
  # Normalized score based on:
  degree = COUNT(edges where entity_id involved)  # Q5
  recency = 1.0 / days_since_last_interaction     # Q1, Q2
  frequency = COUNT(events in last year)          # Q1
  
  relationship_strength = normalize(
      0.4 * degree + 
      0.3 * recency + 
      0.3 * frequency
  )
  ```
- **Использование:** Q11 (кого представить), Q12 (ценность контакта), сортировка

---

### 3. Temporal (временные данные)

#### `first_seen`
- **Type:** TEXT (ISO date)
- **Смысл:** Когда контакт впервые появился в данных
- **Источник:** MIN(event_date) из edges
- **Использование:** Q9 (New vs Old contacts)

#### `last_interaction`
- **Type:** TEXT (ISO date)
- **Смысл:** Последнее взаимодействие (встреча, email)
- **Источник:** MAX(event_date) из edges
- **Использование:** Q2 (Cold contacts), Q1 (Top contacts), status calculation

---

### 4. User-Enriched (ручное обогащение)

#### `notes`
- **Type:** TEXT (nullable)
- **Смысл:** Ручные заметки Ольги
- **Примеры:** "Куратор Paris 2026", "Потенциальный партнёр", "Встретиться весной"
- **Источник:** Web UI (ручной ввод)
- **GIGO:** Структурированные заметки лучше, чем разрозненные файлы

#### `tags`
- **Type:** TEXT (nullable, comma-separated)
- **Примеры:** "paris2026, partner, priority"
- **Источник:** Web UI (ручной ввод)
- **Использование:** Фильтрация, поиск

---

## Миграция: Обогащение существующих данных

### Автоматическое обогащение (из существующих edges):

```python
# Для каждой entity:
# 1. primary_identifier = первый email identifier
# 2. first_seen = MIN(event_date from edges)
# 3. last_interaction = MAX(event_date from edges)
# 4. relationship_strength = calculate from Q5, Q1
# 5. status = 'active' if last_interaction < 6mo else 'cold'
```

### Ручное обогащение (через Web UI):
- `domain` (опционально)
- `notes` (опционально)
- `tags` (опционально)

---

## Индексы (для производительности)

```sql
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);
CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain);
CREATE INDEX IF NOT EXISTS idx_entities_relationship_strength ON entities(relationship_strength DESC);
CREATE INDEX IF NOT EXISTS idx_entities_last_interaction ON entities(last_interaction DESC);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
```

---

## GIGO: Как расширенная схема решает проблему

### Принцип GIGO (Garbage In, Garbage Out):
> "Качество выходных данных определяется качеством входных данных."

### Как схема предотвращает "мусор":

#### 1. Канонизация (Шаг 1) + `primary_identifier`
```sql
primary_identifier TEXT  -- Canonical email
```
- **Проблема:** Дубликаты при ручном вводе
- **Решение:** Проверка `primary_identifier` перед add_fact()
- **GIGO:** Prevent garbage duplicates IN

#### 2. Шлюз add_fact() (Шаг 4) + валидация
```python
def add_fact(...):
    # Validate status
    if status not in ['active', 'cold', 'target', 'archived', 'unknown']:
        raise ValueError("Invalid status")
    
    # Validate domain
    if domain and domain not in VALID_DOMAINS:
        raise ValueError("Invalid domain")
```
- **GIGO:** Validate input data before storing

#### 3. Context Zone (Шаг 2) + провenance
```sql
source_id → sources → raw_data
```
- **Проблема:** Откуда пришёл "мусор"?
- **Решение:** Trace back через source_id
- **GIGO:** Track garbage to source for correction

#### 4. Calculated fields (`relationship_strength`, `status`)
- **Проблема:** Ручной ввод субъективен и неконсистентен
- **Решение:** Автоматический расчёт из объективных данных (edges)
- **GIGO:** Compute quality OUT from validated IN

---

## Использование в Web UI

### Фильтры:
- **Status:** "Показать только active контакты"
- **Domain:** "Показать контакты из design"
- **Relationship strength:** "Топ-20 по силе связи"

### Сортировка:
- По `last_interaction` (для Q2)
- По `relationship_strength` (для Q11, Q12)
- По `first_seen` (для Q9)

### Обогащение:
- Форма для ручного ввода `notes`, `tags`, `domain`
- Авто-сохранение через `add_fact()` с валидацией

---

## Приоритет полей для MVP Web UI

| Поле | Приоритет | Источник | Автоматически? |
|------|-----------|----------|----------------|
| `entity_id` | Критический | System | ✅ Auto |
| `label` | Критический | Contacts/Calendar | ✅ Auto |
| `type` | Критический | Contacts/Calendar | ✅ Auto |
| `primary_identifier` | Высокий | Identifiers table | ✅ Auto |
| `first_seen` | Высокий | MIN(edges.event_date) | ✅ Auto |
| `last_interaction` | Высокий | MAX(edges.event_date) | ✅ Auto |
| `relationship_strength` | Высокий | Calculated | ✅ Auto |
| `status` | Высокий | Calculated from last_interaction | ✅ Auto |
| `domain` | Средний | Manual / LinkedIn | ⚠️ Manual |
| `notes` | Средний | Manual | ⚠️ Manual |
| `tags` | Низкий | Manual | ⚠️ Manual |

**Вывод:** 8 из 11 полей — автоматические. Web UI может работать с минимальным ручным вводом.

---

## Next Steps

1. ✅ **Определить расширенную схему** (done)
2. 🟡 **Обновить `enhanced_graph_db.py`** с новыми полями
3. 🟡 **Создать migration script** для обогащения существующих 464 entities
4. 🟡 **Обновить `add_fact()`** с валидацией новых полей
5. 🟡 **Реализовать Web UI** с использованием новых полей

---

**Статус:** Схема определена, готов к реализации

