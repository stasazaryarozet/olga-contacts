# ОТЧЁТ ДЛЯ GEMINI: v2.1 — Расширенная схема для Деловых Контактов

**Дата:** 2025-11-02, 00:25  
**Статус:** Реализовано, готов к Web UI  
**Вопросы:** 3 критических вопроса перед Web UI

---

## Контекст

После подтверждения Priority 1 (Web UI), реализовал расширенную схему entities для **универсальных деловых контактов** (не CRM, не только клиенты).

**Корректировка терминологии:**
- ❌ CRM (Customer Relationship Management)
- ✅ Деловые Контакты (партнёры, кураторы, коллеги, журналисты, профессора, etc.)

---

## Реализовано

### Расширенная схема entities (8 новых полей):

```sql
entities (
    -- Identity (было)
    entity_id, label, type, created_at,
    
    -- Business Contact Fields (добавлено)
    primary_identifier TEXT,      -- Canonical email
    status TEXT,                   -- 'active', 'cold', 'target', 'archived', 'unknown'
    domain TEXT,                   -- 'design', 'tech', 'academic', 'media', 'business', 'art', 'government'
    relationship_strength REAL,    -- 0.0-1.0 (normalized degree centrality)
    first_seen TEXT,               -- MIN(edges.event_date)
    last_interaction TEXT,         -- MAX(edges.event_date)
    notes TEXT,                    -- User notes (manual)
    tags TEXT,                     -- Comma-separated (manual)
    updated_at TEXT
)
```

### Миграция:

```
contacts_enhanced.db → contacts_v2.db
  ✅ 464 entities
  ✅ 5,050 edges
  ✅ Автоматическое обогащение всех entities
  ✅ 5 индексов для производительности
```

### Результаты обогащения:

```
Status distribution:
  active: 6    (last_interaction < 6 месяцев)
  cold: 1      (last_interaction > 2 года)
  unknown: 457 (нет temporal data или промежуточный период)

Relationship Strength (top 5):
  1. o.g.rozet@gmail.com: 1.372
  2. nsharpanova@britishdesign.ru: 0.720
  3. mivensen@britishdesign.ru: 0.682
  4. infoivanbasov@gmail.com: 0.268
  5. chernysh@britishdesign.ru: 0.220

With fields:
  primary_identifier: 464/464 (100%)
  first_seen: 173/464 (37%)
  last_interaction: 173/464 (37%)
  relationship_strength: 464/464 (100%)
```

---

## ВОПРОСЫ К GEMINI

### Q-G1: Семантика `status` для универсальных деловых контактов

**Текущая реализация:**
```python
if last_interaction < 6 months: status = 'active'
elif last_interaction > 2 years: status = 'cold'
else: status = 'unknown'
```

**Проблема:**
- 457/464 entities имеют status = 'unknown'
- Причина: 63% entities не имеют `last_interaction` (нет event_date в источниках)

**Вопрос:**
Для универсальных деловых контактов (не только клиенты):
1. Корректны ли пороги (6 мес / 2 года)?
2. Что делать с 457 entities без temporal data?
   - **Вариант A:** Оставить 'unknown' (текущее)
   - **Вариант B:** Считать их 'target' (потенциальные, т.к. из Contacts, но нет встреч в Calendar)
   - **Вариант C:** Добавить дополнительный status 'imported' (из Contacts, но нет активности)

**Контекст:**
- Это не "клиенты" (где cold = потеря выручки)
- Это "деловые связи" (где cold = можно возобновить при необходимости)
- Для Ольги может быть важно различать "контакты из адресной книги" vs "контакты с реальным взаимодействием"

---

### Q-G2: `relationship_strength` — корректность для деловых связей

**Текущая реализация:**
```python
relationship_strength = degree / max_degree
```
Где `degree` = COUNT(edges) для entity.

**Результат:**
```
o.g.rozet@gmail.com: 1.372 (!!!)  # > 1.0 из-за undirected graph
nsharpanova@britishdesign.ru: 0.720
mivensen@britishdesign.ru: 0.682
```

**Проблемы:**
1. **Значение > 1.0:** Olga участвует в каждом событии → её degree выше, чем max_degree других entities
2. **Только degree:** Не учитывает recency (последнее взаимодействие) или frequency (частоту)

**Вопросы:**
1. Нужно ли нормализовать relationship_strength к [0, 1]? (сейчас может быть > 1)
2. Нужно ли добавить recency и frequency в формулу?
   ```python
   # Вариант B (weighted):
   degree_norm = degree / max_degree
   recency_norm = 1.0 / (1 + days_since_last_interaction)
   frequency_norm = events_in_last_year / max_events_in_last_year
   
   relationship_strength = 0.4 * degree_norm + 0.3 * recency_norm + 0.3 * frequency_norm
   ```
3. Или простой degree достаточен для MVP?

**Контекст:**
- Для Q11 ("Кого представить X?") и Q12 ("Ценность контакта") эта метрика критична
- Но для Web UI простой degree может быть достаточен (можно улучшить позже)

---

### Q-G3: Поля `domain` и их семантика

**Текущие значения domain:**
```
'design', 'tech', 'academic', 'media', 'business', 'art', 'government', 'other'
```

**Проблема:**
- Это domain = "сфера деятельности" или "тип контакта"?
- Для Organization: domain = сфера (design agency, tech startup)
- Для Person: domain = профессия? роль? или организация, где работает?

**Примеры неоднозначности:**
- Куратор (Olga) работает в дизайн-школе (ВБШД) → domain = 'design' или 'academic'?
- Профессор дизайна → domain = 'design' или 'academic'?
- Журналист, пишущий о дизайне → domain = 'media' или 'design'?

**Вопросы:**
1. Для Person: что означает domain?
   - **A:** Профессиональная сфера (designer, developer, professor)
   - **B:** Организация, где работает (если works_at дизайн-агентство → 'design')
   - **C:** Интересы / специализация (если куратор дизайн-выставок → 'design')

2. Может ли быть несколько domain для одного Person?
   - Например: профессор ('academic') дизайна ('design')
   - Сейчас: один TEXT поле
   - Альтернатива: tags или отдельная таблица person_domains

3. Или domain — это low-priority поле (можно оставить NULL для большинства entities и заполнять вручную при необходимости)?

---

## Готовность к Web UI

**Все технические предпосылки выполнены:**
- ✅ Расширенная схема
- ✅ Миграция
- ✅ Обогащение
- ✅ Индексы
- ✅ Тесты

**Но перед Web UI критично определить:**
1. Семантику `status` для entities без temporal data (457/464)
2. Корректность `relationship_strength` (простой degree vs weighted)
3. Семантику `domain` для Person (профессия vs организация vs интересы)

**Без этого Web UI будет показывать некорректные данные:**
- Фильтр по status = 'active' → только 6 entities (98% будут 'unknown')
- Сортировка по relationship_strength → Olga на 1 месте с 1.372 (выше max)
- Фильтр по domain → пустой (все NULL)

---

## Рекомендуемый порядок ответов:

**Priority 1 (критичный для Web UI):**
- Q-G1: Семантика status (что делать с 457 'unknown')

**Priority 2 (влияет на качество рекомендаций):**
- Q-G2: relationship_strength (simple vs weighted)

**Priority 3 (можно отложить):**
- Q-G3: domain (заполнить вручную через Web UI позже)

---

**Operational Model:** v6.2 (ROI-Driven + Constraint-Driven)  
**Вопрос:** Критично ли исправить эти 3 вопроса до Web UI, или можно начать Web UI с текущей схемой и улучшить потом?

