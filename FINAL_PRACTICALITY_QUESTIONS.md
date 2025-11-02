# ФИНАЛЬНЫЕ ВОПРОСЫ: MVP Practicality

**Дата:** 2025-11-01  
**Контекст:** Получены детальные ответы на вопросы уровня реализации. Требуется уточнение trade-offs MVP.

---

## ВОПРОСЫ О ПРАКТИЧЕСКОЙ РЕАЛИЗУЕМОСТИ MVP

### 1. MVP без Probabilistic ER: Приемлемый trade-off?

**Проблема:**
- MVP включает только **deterministic ER** (exact match email/linkedin/name+org)
- **Probabilistic ER отложен** на post-MVP
- Это означает: граф MVP будет иметь множество дубликатов

**Пример:**
```
(:Person {name: "Ольга Розет"})
(:Person {name: "О. Розет"})
(:Person {name: "Olga Rozet"})
```

Все три узла будут существовать одновременно (deterministic rules их не сольют).

**Вопрос:**
Насколько критична эта проблема для **демонстрации концепции**?

Вариант A: **Приемлемо для MVP**
- Граф будет "грязным", но функциональным
- Координатор увидит дубликаты и поймёт необходимость probabilistic ER
- Можно добавить в post-MVP с приоритетом 1

Вариант B: **Неприемлемо — нужен MVP+ с базовым probabilistic ER**
- Хотя бы простой string similarity (Levenshtein > 0.85) для Person names
- Без этого граф будет слишком "разреженным" и не покажет value

Какой вариант рекомендуешь?

---

### 2. MVP без TruthFinder: Качество при противоречиях

**Проблема:**
- TruthFinder отложен на post-MVP
- MVP hack: `B(f) = C(f,s)` (believability = LLM confidence)
- Это означает: **противоречия не разрешаются**

**Пример конфликта:**
```
Source 1 (confidence 0.95): Ольга works_at ВБШД (2018-2020)
Source 2 (confidence 0.93): Ольга works_at ВБШД (2018-present)
```

В MVP оба факта будут в графе с believability ≈ 0.95 и 0.93.

**Вопрос:**
Как Graph API (Q6) должен обрабатывать такие конфликты в MVP?

Вариант A: **Возвращать все факты**
```graphql
{
  person(name: "Ольга Розет") {
    workHistory {  # Массив
      org: "ВБШД"
      start: "2018"
      end: "2020"
      believability: 0.95
    },
    {
      org: "ВБШД"
      start: "2018"
      end: null
      believability: 0.93
    }
  }
}
```
Клиент сам выбирает.

Вариант B: **Возвращать факт с highest believability**
```graphql
# Только первый (0.95 > 0.93)
```

Вариант C: **Возвращать с warning о конфликте**
```json
{
  "data": {...},
  "warnings": ["Conflict detected for works_at ВБШД"]
}
```

Какой подход для MVP?

---

### 3. Seed Data: Конкретный формат и содержание

Ты сказал: **"Effort = 1 hour"** для seed data.

**Неясно:**

**3.1. Формат входных данных:**

Вариант A (Простой список URL):
```yaml
seed_sources:
  - https://olgarozet.com/bio
  - https://bvshd.ru/teachers/rozet
  - https://linkedin.com/in/olgarozet
  - https://designmagazine.ru/interview-rozet-2023
```

Вариант B (Структурированный seed):
```yaml
anchor:
  name: "Ольга Розет"
  linkedin: "linkedin.com/in/olgarozet"
  
seed_entities:
  organizations:
    - ВБШД
    - Творческая мастерская Ольги Розет
  people:
    - Наталья Логинова
    
seed_sources:
  - url: https://...
    type: website_bio
    authority: 1.0
```

**Какой формат для MVP?** Вариант A проще (Effort → 0), но Вариант B даёт anchor nodes для snowballing (post-MVP).

**3.2. Кто собирает seed?**
- Координатор вручную (Google search за 1 час)?
- Или есть полуавтоматический способ (LLM generates seed URLs по имени персоны)?

---

### 4. MVP без Snowballing: Размер графа

**Проблема:**
- Snowballing отложен на post-MVP
- MVP работает только с **seed sources** (10-20 URL)
- Это означает: граф будет очень маленьким

**Вопрос:**
Какой **минимальный размер графа** демонстрирует value системы?

Оценка для 10 seed URLs:
```
10 URLs × 3 persons/URL avg = 30 persons
30 persons × 1.5 relations/person = 45 relations
```

Граф из 30 узлов и 45 рёбер — это достаточно для демонстрации концепции?

Или нужно увеличить seed до 50-100 URLs (но это нарушает "Effort = 1 hour")?

---

### 5. Graph API: GraphQL vs Cypher для MVP

Ты упомянул оба варианта:
> "Простой GraphQL endpoint на AWS AppSync или Lambda URL с Cypher"

**Вопрос:**
Какой конкретно выбрать для MVP?

**Trade-offs:**

| Аспект | GraphQL (AppSync) | Cypher (Lambda endpoint) |
|--------|------------------|-------------------------|
| **Сложность реализации** | Высокая (нужен schema design) | Низкая (прокси к Neo4j) |
| **User experience** | Отличный (typed, discoverable) | Требует знания Cypher |
| **Гибкость** | Ограничена схемой | Полная (любой запрос) |
| **Security** | Встроенная (AppSync) | Требует ручной реализации |
| **Time to implement** | 2-3 дня | 1 день |

Для MVP (2-3 недели) рекомендуешь GraphQL или Cypher?

---

### 6. Error Handling: Кто смотрит DLQ?

Ты описал self-healing через DLQ:
> "Healing — это ручной просмотр DLQ координатором раз в неделю"

**Вопрос:**
Какой конкретный workflow для координатора?

**6.1. Как координатор видит DLQ?**
- AWS Console (ручной login)?
- Еженедельный email digest с содержимым DLQ?
- Dashboard с кнопкой "Retry failed messages"?

**6.2. Что делать с сообщениями в DLQ?**
- Просто retry (если transient error)?
- Fix source (если malformed)?
- Ignore (если source действительно невалиден)?

Нужен ли **admin UI** для управления DLQ, или достаточно AWS Console?

---

### 7. Temporal Normalization: Edge cases

Ты описал нормализацию:
> "осень 2018" → "2018-09-01"

**Вопрос:**
Как обрабатывать **ambiguous temporal expressions**?

**Примеры:**
- "в начале 2020-х" → `start: "2020-01-01", end: "2025-12-31"`?
- "несколько лет назад" (в статье от 2023) → `start: "2020-01-01"` (2023-3)?
- "с 2018 по настоящее время" → `end: null` ✓
- "2018-2020" → `start: "2018-01-01", end: "2020-12-31"` ✓

Нужно ли в Lambda иметь **temporal expression parser** (сложно)?

Или достаточно **simple heuristics** + fallback to null:
```python
if "present" in end_raw or "настоящее" in end_raw:
    end_date = None
elif matches_YYYY(end_raw):
    end_date = f"{end_raw}-12-31"
else:
    end_date = None  # Fallback
```

---

### 8. Cost: Free tier реальность

Ты показал:
> Neo4j Aura Free Tier (50k V, 175k E) может быть достаточен для MVP

**Вопрос:**
При каких условиях MVP **останется в free tier** Neo4j?

Оценка:
```
Seed: 10 URLs × 30 persons = 300 V
Post-seed (1 month, no snowballing): ещё 100 V?
Total MVP: ~500 V, 1000 E
```

Это **<< 50k limit**, так что free tier покрывает MVP.

Но **когда система перерастёт free tier**?
- При включении Snowballing (post-MVP)?
- Примерная оценка: сколько месяцев continuous ingestion до 50k V?

Нужен ли **migration plan** от Free → Professional в TASK_SOW.md?

---

## ИТОГО

8 вопросов о практической реализации MVP:

1. **Probabilistic ER:** Приемлем ли MVP без него (с дубликатами)?
2. **TruthFinder:** Как Graph API обрабатывает конфликты без него?
3. **Seed format:** Конкретный формат входных данных и кто собирает?
4. **Graph size:** Достаточно ли 30 узлов для демонстрации?
5. **Graph API:** GraphQL vs Cypher для MVP (учитывая timeline)?
6. **DLQ workflow:** Конкретный процесс для координатора?
7. **Temporal parser:** Simple heuristics vs полноценный parser?
8. **Free tier limits:** Когда система перерастёт и нужен ли migration plan?

Эти ответы определят **реалистичность scope** и **качество deliverable** для MVP.

