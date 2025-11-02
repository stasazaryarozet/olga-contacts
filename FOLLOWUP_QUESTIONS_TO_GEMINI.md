# FOLLOW-UP ВОПРОСЫ К GEMINI: От архитектуры к коду

**Дата:** 2025-11-01  
**Контекст:** Получены ответы на 7 критических вопросов. Требуется уточнение для implementation.

---

## ВОПРОСЫ УРОВНЯ РЕАЛИЗАЦИИ

### 1. Промпт для Claude: Адаптивность vs Универсальность

Ты привёл отличный example system prompt для Claude 3.5 Sonnet.

**Проблема:** Источники разнородны:
- Личный сайт (структурированный HTML, bio)
- Статья в СМИ (неструктурированный текст, множество персон)
- LinkedIn (semi-structured, текущая должность)
- Email (крайне контекстный, может быть thread)

**Вопрос:**
Нужен ли **один универсальный промпт** для всех типов источников?

Или следует использовать **source-type-aware prompting**:
```python
if source_type == "linkedin":
    prompt = linkedin_focused_prompt  # акцент на текущую роль
elif source_type == "media":
    prompt = media_focused_prompt  # акцент на упоминания в контексте
```

Если второе — какие конкретно модификации промпта для каждого типа источника?

---

### 2. Snowballing: Конкретика генерации запросов

Описан BFS-алгоритм расширения графа:
> "Для каждого V₁ система автономно генерирует поисковый запрос"

**Неясно:**

**2.1. Query Generation Pattern:**
Какой конкретно pattern для генерации запросов?

Вариант A (Template-based):
```python
query = f'"{anchor_name}" "{new_entity_name}"'
# Пример: "Ольга Розет" "ВБШД"
```

Вариант B (LLM-generated):
```python
query = llm.generate_search_query(
    anchor="Ольга Розет",
    entity="ВБШД",
    context="works_at"
)
# LLM может сгенерировать: "Ольга Розет преподаватель ВБШД"
```

Какой подход SOTA для этой задачи?

**2.2. Depth Limit:**
Как избежать дрейфа? Нужен ли hard limit:
```
Max BFS depth = 2  
(Ольга → её контакты → контакты её контактов — STOP)
```

Или distance decay:
```
Relevance Score = confidence × (1 / distance_from_anchor)
Обрабатывать только если Relevance > threshold
```

**2.3. Search API:**
Какой конкретно search API использовать для MVP?
- Google Custom Search JSON API (платный, 100 запросов/день бесплатно)
- SerpAPI (агрегатор, платный)
- Scrapy + Google search (рискованно, anti-bot)

---

### 3. Source Authority: Bootstrap без априорного знания

Ты предложил:
```
A(olgarozet.com) = 1.0  # seed
A(bvshd.ru) = 0.95
```

**Проблема:** Что если у Ольги нет личного сайта? Или координатор не знает заранее "авторитетные" домены?

**Вопрос:**
Как инициализировать A(s) для **первичных seed sources** автономно?

Вариант A (Domain Authority API):
```python
A(s) = moz_domain_authority(extract_domain(s)) / 100
```

Вариант B (Heuristic):
```python
if ".edu" or ".gov" in domain: A(s) = 0.95
elif domain in ["linkedin.com", "wikipedia.org"]: A(s) = 0.90
else: A(s) = 0.80
```

Вариант C (First-class sources):
```python
# Все источники, предоставленные вручную в seed, получают A(s) = 1.0
# Остальные = 0.8
```

Какой подход рекомендуешь для MVP?

---

### 4. Temporal Extraction: Как извлекать даты?

В твоём example prompt нет explicit instruction для temporal data.

**Вопрос:**
Должен ли Claude извлекать temporal bounds (start/end) для каждой связи E?

Если да, нужно ли модифицировать schema в промпте:
```json
{
  "relation": "works_at",
  "subject": "Ольга Розет",
  "object": "ВБШД",
  "temporal": {
    "start": "2018" | "2018-09" | "2018-09-01" | null,
    "end": "present" | "2022" | null
  },
  "confidence": 0.96
}
```

**Проблемы:**
- Granularity: Разрешить "2018" и "2018-09-01" одновременно? (Нормализовать в Neo4j?)
- "present": Как хранить? (null end_date или специальное значение "9999-12-31"?)
- Отсутствие дат: Если текст не содержит temporal info, оставлять null или отбрасывать связь?

Какие best practices для temporal extraction в Neo4j?

---

### 5. TruthFinder: Схема данных в Neo4j

Алгоритм TruthFinder требует:
- `sources_claiming(f)`: Какие источники заявили факт f?
- `facts_claimed_by(s)`: Какие факты заявлены источником s?

**Вопрос:**
Как это хранить в Neo4j? Какая конкретная схема графа?

Вариант A (Fact Reification):
```
(:Person)-[:WORKS_AT {id: "fact_123"}]->(:Organization)
(:Source {url: "..."})-[:CLAIMS {confidence: 0.9}]->(:Fact {id: "fact_123"})
```

Вариант B (Direct provenance on edge):
```
(:Person)-[:WORKS_AT {
  sources: ["url1", "url2"],
  confidences: [0.9, 0.95],
  believability: 0.93
}]->(:Organization)
```

Какой подход рекомендуешь? Вариант A более гибкий, но усложняет запросы. Вариант B проще, но как хранить конфликтующие факты?

---

### 6. MVP Scope: Что входит в "2-3 недели"?

Ты оценил timeline: **2-3 недели разработки**.

**Вопрос:**
Что конкретно входит в этот scope? Checklist:

- [ ] Infrastructure setup (Lambda, SQS, S3, Neo4j Aura)
- [ ] Ingestion pipeline (+ source connectors)
- [ ] IE pipeline (Claude API integration)
- [ ] Entity Resolution (deterministic + probabilistic)
- [ ] TruthFinder (self-consistency batch job)
- [ ] Graph API (GraphQL или Cypher endpoint)
- [ ] Dashboard (metrics monitoring)
- [ ] Seed processing (initial 5-10 sources)
- [ ] Snowballing mechanism (BFS)
- [ ] Testing (unit + integration)

Все вышеперечисленное за 2-3 недели? Или это только core pipeline (первые 5 пунктов)?

---

### 7. Cost Breakdown: $50-150/month

Ты оценил TCO MVP: **$50-150/month**.

**Вопрос:**
Дай breakdown по компонентам:

```yaml
claude_api:
  assumption: X docs/month, Y tokens/doc
  cost: $...
  
neo4j_aura:
  tier: Professional / Enterprise?
  cost: $...
  
aws_lambda:
  invocations: ...
  cost: $...
  
s3_storage:
  data_size: ... GB
  cost: $...
  
sqs:
  messages: ...
  cost: $...
  
total: $...
```

Это поможет понять, где основные затраты и как оптимизировать.

---

### 8. Error Handling: Self-Healing стратегия

Ты упомянул "self-healing" как ключевое свойство.

**Вопрос:**
Какая конкретная стратегия для error handling в serverless MVP?

**Сценарии:**
- Claude API unavailable (503)
- Claude API rate limit (429)
- Neo4j Aura connection timeout
- Malformed source (невалидный HTML)
- LLM hallucination (confidence = 0.0 для всех extractions)

**Для каждого сценария:**
- Retry policy? (Exponential backoff?)
- Dead Letter Queue?
- Fallback behavior?
- Alert mechanism?

Опиши error handling architecture для serverless stack.

---

## ИТОГО

8 вопросов для финализации implementation plan:

1. **Промпт-стратегия:** Универсальный vs source-aware?
2. **Query generation:** Конкретный pattern для snowballing
3. **Source Authority:** Инициализация без априорного знания
4. **Temporal extraction:** Schema и best practices
5. **TruthFinder storage:** Neo4j data model
6. **MVP scope:** Детальный checklist
7. **Cost breakdown:** Компоненты TCO
8. **Error handling:** Self-healing в serverless

С ответами на эти вопросы можно писать код, а не только архитектуру.

