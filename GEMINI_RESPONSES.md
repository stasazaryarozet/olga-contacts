# ОТВЕТЫ GEMINI: Уточнение архитектуры

**Дата получения:** 2025-11-01  
**Статус:** Принято к реализации

---

## 1. РУССКИЙ ЯЗЫК + КРЕАТИВНЫЙ ДОМЕН

### Решение: Claude 3.5 Sonnet

**Модель:** Claude 3.5 Sonnet (API)
- SOTA в гуманитарных/нюансированных доменах
- Превосходит GPT-4o в zero-shot reasoning для неструктурированных отношений
- Лучший выбор для смешанного русско-английского текста

**Локальные модели (rugpt, saiga):** Неприменимы без fine-tuning (нарушает Effort → 0)

**Промпт-стратегия:**
- Schema-in-Prompt + Open Relation Extraction
- Chain-of-Thought + Strict JSON output
- Domain-specific schema с возможностью `relation_custom`

---

## 2. API vs SELF-HOSTED

### Решение: API для MVP

**Деградация качества:** Катастрофическая при переходе на quantized 8B модели
- Confidence > 0.95 недостижим на малых локальных моделях для zero-shot RE
- Требуются frontier models (GPT-4o, Sonnet 3.5, Llama 405B)

**Экономика:**
```
Cost_API = (Docs/Month) × (Avg Tokens/Doc) × (Price/Token)
Cost_Local = (GPU/hr × 24 × 30) + Ops Cost

Break-even: >15-20M tokens/hour непрерывно
```

**Вывод:** Для MVP с bursty нагрузкой API значительно дешевле и качественнее.

---

## 3. SEED DATA STRATEGY

### Решение: Snowballing от ручного seed

**Минимальный seed (Effort = 1 hour):**
- 5-10 ключевых организаций (ВБШД, мастерская, проекты)
- 5-10 ключевых людей (со-кураторы, менторы)
- 5-10 ключевых URL (личный сайт, LinkedIn, интервью)

**Стратегия расширения (BFS):**
- Level 0: Обработать seed sources → извлечь V₁ и E₁
- Level 1: Для каждого V₁ генерировать поисковые запросы автономно
- Level 2: Top 5 URL добавляются в очередь
- Результат: После 100 документов (snowballing) → avg degree 3-5

---

## 4. ENTITY RESOLUTION

### Решение: Hybrid ER + Probabilistic Links

**Pass 1 - Deterministic (Safe Merge):**
```
IF exact_match(email) → MERGE
IF exact_match(linkedin_url) → MERGE  
IF exact_match(full_name) AND exact_match(organization) → MERGE
```

**Pass 2 - Probabilistic:**
```
IF p > 0.99 → Auto-Merge
IF 0.90 < p ≤ 0.99 → Create edge (V1, potential_match, V2, confidence: p)
IF p ≤ 0.90 → Ignore
```

**Ключевое:** Не создавать "human review queue" (нарушает Effort → 0). Вместо этого — probabilistic links в графе.

---

## 5. SELF-CONSISTENCY АЛГОРИТМ

### Решение: TruthFinder (Data Fusion)

**Концепция:**
- A(s): Authority источника (0.0-1.0)
- B(f): Believability факта (0.0-1.0)
- C(f,s): LLM confidence факта из источника

**Алгоритм (итеративный, 3-5 циклов):**

```python
# Инициализация
A(s) = 0.8  # базовое доверие
A(olgarozet.com) = 1.0  # seed
B(f) = 0.5

for _ in range(MAX_ITERATIONS):
    # 1. Update Fact Believability
    for f in F:
        trust_sum = 0
        for s in sources_claiming(f):
            influence = log(1 / (1 - A(s)))
            trust_sum += influence * C(f, s)
        B(f) = 1 / (1 + exp(-trust_sum))  # Sigmoid
    
    # 2. Update Source Authority
    for s in S:
        believability_sum = sum(B(f) for f in facts_claimed_by(s))
        A(s) = believability_sum / num_facts_claimed_by(s)
```

**Conflict Detection:** Автоматический — факт с большим B(f) "побеждает" конфликтующий.

---

## 6. MVP АРХИТЕКТУРА (80/20)

### Решение: Serverless Stack

| Компонент | Enterprise | MVP (Serverless) |
|-----------|-----------|------------------|
| **Ingestion** | Kafka | AWS SQS / Cloud Pub/Sub |
| **Storage** | Data Lake | S3 / Cloud Storage |
| **Processing** | Flink + K8s | Lambda / Cloud Functions |
| **Orchestration** | K8s | Step Functions / Workflows |
| **IE (LLM)** | Self-hosted | Claude API |
| **Graph DB** | Neo4j (self-hosted) | Neo4j Aura (managed) |

**Trade-offs:**
- ❌ Теряем: Stateful processing, реальный streaming
- ❌ Теряем: Нативный replay (Kafka)
- ✅ Сохраняем: Raw data в S3 → ручной replay возможен
- ✅ Сохраняем: Лёгкая миграция на enterprise stack

**Self-consistency:** Реализовать как batch job (раз в час), не streaming.

---

## 7. SUCCESS METRICS

### Dashboard: Autonomous Graph Health

**Pipeline Health:**
- Docs Processed / 24h
- Avg Latency / Doc
- LLM API Error Rate < 1%
- Ingest Queue Depth < 100

**Graph Size:**
- Total Nodes (V) — рост
- Total Edges (E) — рост
- Avg Degree — медленный рост

**Graph Quality:**
- New V / New E Ratio — баланс
- ER Merge Rate — 5-10%
- Probabilistic Link Count — 2-5% узлов

**Confidence:**
- P90 (90% рёбер) > 0.9 confidence
- Avg Source Authority — 0.5-0.8
- Conflict Rate < 5%

**Freshness:**
- % V/E updated < 30 days — высокий
- Anomalies Detected — 0

---

## ИТОГОВАЯ КОНФИГУРАЦИЯ MVP

```yaml
model: Claude 3.5 Sonnet (API)
infrastructure: Serverless (AWS Lambda + Step Functions + SQS)
graph_db: Neo4j Aura (managed)
entity_resolution: Hybrid (deterministic + probabilistic links)
self_consistency: TruthFinder (batch, hourly)
seed_effort: 1 hour (Ольга + координатор)
expansion: Snowballing (BFS)
confidence_threshold: 0.90 (E), 0.99 (merge)
estimated_tco: $50-150/month (MVP)
estimated_timeline: 2-3 недели разработки
```

---

## ГОТОВНОСТЬ К РЕАЛИЗАЦИИ

Все критические вопросы получили конкретные, реализуемые ответы.

**Следующий шаг:** Создание TASK_SOW.md — формализованного технического задания для инженера.

