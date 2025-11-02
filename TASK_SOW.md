# ТЕХНИЧЕСКОЕ ЗАДАНИЕ: Автономная система построения социального графа (MVP)

**Версия:** 1.0  
**Дата:** 2025-11-01  
**Статус:** Утверждено к реализации  
**Timeline:** 2-3 недели (1 senior engineer)  
**Budget:** $50-150/month

---

## 1. ЦЕЛЬ ПРОЕКТА

Создать **MVP автономной системы**, которая:
- Принимает список публичных источников (URLs)
- Извлекает структурированный граф деловых связей персоны (Ольга Розет)
- Сохраняет результаты в graph database
- Работает без участия человека после инициализации

**Критерий успеха MVP:** Демонстрация трансформации "unstructured text → structured graph" на 10-20 seed sources.

---

## 2. АРХИТЕКТУРА

### 2.1. Компоненты

```
┌──────────────┐
│  Seed Data   │ (10-20 URLs, координатор, 1 hour)
└──────┬───────┘
       │
       v
┌──────────────┐
│   AWS S3     │ (Raw data storage + Data provenance)
└──────┬───────┘
       │
       v
┌──────────────┐
│   AWS SQS    │ (Ingestion queue)
└──────┬───────┘
       │
       v
┌──────────────────────────────────────────┐
│  Lambda: IE Pipeline                     │
│  - Fetch content                         │
│  - Claude 3.5 Sonnet API (NER/RE)       │
│  - Temporal normalization (LLM-based)    │
└──────┬───────────────────────────────────┘
       │
       v
┌──────────────────────────────────────────┐
│  Lambda: Graph Loader                    │
│  - Deterministic Entity Resolution       │
│  - Fact Reification (Neo4j)             │
└──────┬───────────────────────────────────┘
       │
       v
┌──────────────┐
│  Neo4j Aura  │ (Graph DB, Free Tier)
│  (Free Tier) │
└──────┬───────┘
       │
       v
┌──────────────┐
│ Cypher API   │ (Lambda endpoint для queries)
└──────────────┘
```

### 2.2. Orchestration

AWS Step Functions:
```
StartExecution
  ├─> IngestToS3
  ├─> SendToSQS
  └─> (SQS triggers Lambda IE Pipeline)
```

### 2.3. Error Handling

- **Retry:** SQS visibility timeout + maxReceiveCount: 3
- **DLQ:** Dead Letter Queue для failed messages
- **Monitoring:** CloudWatch Alarm → SNS → Email координатору

---

## 3. ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ

### 3.1. Information Extraction (IE)

**LLM:** Claude 3.5 Sonnet API

**Prompting Strategy:** Source-type-aware

#### Базовый промпт (core_prompt.xml):

```xml
<system>
Ты — эксперт-аналитик по извлечению профессиональных связей из текста. 
Твоя задача — извлечь все узлы (V) и рёбра (E) из предоставленного текста. 
Ольга Розет — anchor-узел.

ОПРЕДЕЛЕНИЯ УЗЛОВ (V):
- Person: {name: string, title: string | null}
- Organization: {name: string, type: "company" | "gallery" | "school" | "event"}

ОПРЕДЕЛЕНИЯ СВЯЗЕЙ (E):
- works_at (Person, Organization)
- curated (Person, Event | Organization)
- co_curated (Person, Person, Event)
- taught_at (Person, Organization)
- studied_at (Person, Organization)
- participated_in (Person, Event | Organization)

ЕСЛИ ты найдёшь сильную профессиональную связь, которой НЕТ в schema,
создай для неё `relation_custom: "..."`.

Для каждого V и E, назначь `confidence` (0.0-1.0).

TEMPORAL DATA:
Извлеки temporal bounds для каждой связи:
- start_raw: как написано в тексте
- end_raw: как написано в тексте
- start_iso: нормализуй в YYYY-MM-DD (или null)
- end_iso: нормализуй в YYYY-MM-DD (или null, если "present")

Выведи результат ИСКЛЮЧИТЕЛЬНО в формате JSON-массива.
</system>

<user>
<text>
{CONTENT}
</text>
</user>
```

#### Source-type модификации:

**linkedin:**
```
ВНИМАНИЕ: Ты анализируешь профиль LinkedIn. Данные полуструктурированы. 
'Текущая должность' и 'Опыт работы' — факты с высоким confidence.
```

**media:**
```
ВНИМАНИЕ: Ты анализируешь статью. В ней может быть много V. 
Фокусируйся ИСКЛЮЧИТЕЛЬНО на связях, касающихся 'Ольга Розет'.
Контекст статьи (e.g., 'на выставке X') важен.
```

**website_bio:**
```
ВНИМАНИЕ: Страница 'Обо мне'. Информация имеет высокий authority.
Удели внимание спискам проектов и аффилиаций.
```

#### Output Schema:

```json
{
  "entities": [
    {
      "type": "Person",
      "name": "Ольга Розет",
      "title": "Дизайнер, преподаватель"
    }
  ],
  "relations": [
    {
      "subject": {"name": "Ольга Розет", "type": "Person"},
      "relation": "works_at",
      "object": {"name": "ВБШД", "type": "Organization"},
      "temporal": {
        "start_raw": "2018",
        "end_raw": "present",
        "start_iso": "2018-01-01",
        "end_iso": null
      },
      "context": "Ольга преподаёт в ВБШД с 2018 года",
      "confidence": 0.96
    }
  ]
}
```

### 3.2. Entity Resolution (Deterministic только)

**Rules (в порядке применения):**

```python
def deterministic_er(v1, v2):
    # Rule 1: Exact email match
    if v1.email and v2.email and v1.email == v2.email:
        return MERGE
    
    # Rule 2: Exact LinkedIn URL match
    if v1.linkedin and v2.linkedin and v1.linkedin == v2.linkedin:
        return MERGE
    
    # Rule 3: Exact name + organization
    if (v1.full_name == v2.full_name and 
        v1.organization == v2.organization and 
        v1.organization is not None):
        return MERGE
    
    # Probabilistic ER — POST-MVP
    return NO_MERGE
```

**Ожидаемый результат:** Граф будет содержать дубликаты ("Ольга Розет", "О. Розет"). Это **фича для демо**, не баг.

### 3.3. Neo4j Schema (Fact Reification)

```cypher
// 1. Узлы Сущностей (V)
CREATE (p:Person {
    name: "Ольга Розет", 
    canonical_id: "v1"
})

CREATE (o:Org {
    name: "ВБШД", 
    canonical_id: "v2"
})

CREATE (s:Source {
    url: "https://...", 
    authority: 1.0,  // seed = 1.0
    ingested_at: datetime()
})

// 2. Узел Факта (Claim)
CREATE (f:Fact {
    id: "fact_123",
    type: "works_at",
    start_date: date("2018-01-01"),
    end_date: null,  // "present"
    believability: 0.96,  // = LLM confidence (MVP hack)
    context: "Ольга преподаёт в ВБШД с 2018"
})

// 3. Связи
CREATE (s)-[:CLAIMS {confidence_llm: 0.96}]->(f)
CREATE (f)-[:SUBJECT]->(p)
CREATE (f)-[:OBJECT]->(o)
```

### 3.4. Graph API (Cypher Endpoint)

**Lambda Function:** `/query`

**Request:**
```json
{
  "cypher": "MATCH (p:Person {name: 'Ольга Розет'})-[:SUBJECT]-(f:Fact)-[:OBJECT]->(o) WHERE f.type='works_at' RETURN o.name, f.start_date, f.end_date, f.believability ORDER BY f.believability DESC"
}
```

**Response:**
```json
{
  "results": [
    {
      "o.name": "ВБШД",
      "f.start_date": "2018-01-01",
      "f.end_date": null,
      "f.believability": 0.96
    }
  ]
}
```

**Security (MVP):** Basic API Key в Lambda authorizer.

---

## 4. SCOPE MVP (2-3 НЕДЕЛИ)

### Включено:

- [x] Infrastructure setup (Terraform/CDK: SQS, S3, Lambda, Neo4j Aura)
- [x] Ingestion pipeline (S3 → SQS → Lambda)
- [x] IE pipeline (Claude API integration + source-type routing)
- [x] Deterministic Entity Resolution
- [x] Neo4j Fact Reification schema
- [x] Graph Loader (Lambda → Neo4j)
- [x] Cypher API endpoint
- [x] Seed processing script (`run_seed.py`)
- [x] Error handling (DLQ + CloudWatch)
- [x] Basic unit tests

### НЕ включено (Post-MVP):

- [ ] Probabilistic Entity Resolution
- [ ] TruthFinder (self-consistency algorithm)
- [ ] Snowballing (BFS expansion)
- [ ] GraphQL API
- [ ] Dashboard (metrics monitoring)
- [ ] Integration/E2E tests

---

## 5. DELIVERABLES

### 5.1. Code

**Структура репозитория:**
```
contacts/
├── infrastructure/
│   └── main.tf (или cdk.py)
├── lambdas/
│   ├── ie_pipeline/
│   │   ├── handler.py
│   │   ├── prompts/
│   │   │   ├── core_prompt.xml
│   │   │   ├── linkedin.xml
│   │   │   └── media.xml
│   │   └── requirements.txt
│   ├── graph_loader/
│   │   ├── handler.py
│   │   ├── er_rules.py
│   │   └── requirements.txt
│   └── query_api/
│       ├── handler.py
│       └── requirements.txt
├── scripts/
│   ├── run_seed.py
│   └── seed.txt.example
├── tests/
│   └── unit/
└── README.md
```

### 5.2. Документация

- **README.md:** Setup instructions, deployment, usage
- **ARCHITECTURE.md:** Диаграммы, объяснение design decisions
- **API.md:** Cypher endpoint documentation + примеры запросов

### 5.3. Demo Package

- **seed.txt:** 10-20 URLs для демонстрации
- **demo_queries.cypher:** Набор готовых запросов для демо
- **demo_script.md:** Сценарий демонстрации

---

## 6. ACCEPTANCE CRITERIA

### 6.1. Функциональные

1. ✅ Система обрабатывает seed.txt (10-20 URLs) автономно
2. ✅ Для каждого URL создаётся (:Source) узел в Neo4j
3. ✅ Извлечено ≥ 30 (:Person) или (:Org) узлов
4. ✅ Извлечено ≥ 45 (:Fact) узлов с типом relation
5. ✅ Все Facts имеют believability ∈ [0.0, 1.0]
6. ✅ Deterministic ER объединил ≥ 2 дубликата (если есть exact matches)
7. ✅ Cypher API возвращает результаты за < 2 сек
8. ✅ Malformed URLs попадают в DLQ (не крашат систему)

### 6.2. Нефункциональные

1. ✅ Idempotency: Повторная обработка URL не создаёт дубликаты Facts
2. ✅ Cost: Обработка 20 URLs стоит < $5
3. ✅ Timeline: Обработка 20 URLs завершается за < 30 минут
4. ✅ Monitoring: CloudWatch Alarm срабатывает при DLQ > 0

---

## 7. COST ESTIMATE

```yaml
claude_api:
  docs: 20 (seed)
  tokens_per_doc: 6k (5k input + 1k output)
  cost: (20 × 6k × $3/1M) + (20 × 1k × $15/1M) = $0.66

neo4j_aura:
  tier: Free (50k nodes, 175k relationships)
  cost: $0

aws:
  lambda: ~20 invocations × 10 sec = $0.01
  s3: 1 GB = $0.02
  sqs: 20 messages = $0.00
  
total_per_run: $0.69
monthly_estimate: $0.69 × 3 runs (testing) = ~$2
```

**MVP Budget:** < $5/month (во время разработки)

**Post-deployment:** $50-150/month (при continuous ingestion, см. GEMINI_FINAL_ANSWERS.md)

---

## 8. РИСКИ И MITIGATION

| Риск | Вероятность | Impact | Mitigation |
|------|------------|--------|------------|
| Claude API rate limit | Средняя | Высокий | Exponential backoff + DLQ |
| Neo4j Free Tier exhausted | Низкая | Средний | Monitoring (NodeCount metric) |
| Malformed HTML crashes pipeline | Высокая | Низкий | Try-catch + DLQ |
| Seed URLs недоступны (404) | Средняя | Низкий | HTTP error handling + DLQ |
| Temporal extraction fails | Средняя | Низкий | Fallback: temporal.start_iso = null |

---

## 9. POST-MVP ROADMAP

**Priority 1 (следующие 2-3 недели):**
- Probabilistic Entity Resolution (GNN-based)
- TruthFinder (self-consistency batch job)

**Priority 2 (месяц 2):**
- Snowballing (BFS expansion)
- Dashboard (metrics monitoring)

**Priority 3 (месяц 3):**
- GraphQL API
- Admin UI для DLQ management

---

## 10. REFERENCES

- `AI_PROMPT_CONTACT_BUILDER.md` — Исходный запрос
- `ARCHITECTURE_RESPONSE.md` — Полная архитектура от Gemini
- `GEMINI_RESPONSES.md` — Ответы на критические вопросы
- `GEMINI_FINAL_ANSWERS.md` — Практические trade-offs MVP

---

**Утверждено к реализации:** 2025-11-01  
**Estimated completion:** 2025-11-22 (3 weeks)

