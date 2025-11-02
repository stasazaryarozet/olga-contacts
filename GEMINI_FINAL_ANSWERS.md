# ФИНАЛЬНЫЕ ОТВЕТЫ: MVP Practicality

**Дата получения:** 2025-11-01  
**Статус:** Принято. Готовность к созданию TASK_SOW.

---

## 1. MVP БЕЗ PROBABILISTIC ER

**Решение:** Приемлемо для MVP (Вариант A)

**Обоснование:**
- Цель MVP — доказать жизнеспособность пайплайна (Ingest → IE → Graph Load)
- "Грязный" граф с дубликатами — **сильнейшая аргументация** для финансирования post-MVP
- Попытка добавить "базовый Levenshtein" — MVP-trap (усложнит код, не даст 99% точности)

---

## 2. MVP БЕЗ TRUTHFINDER

**Решение:** Возвращать все факты (Вариант A)

**Обоснование:**
- Вариант B (highest believability) — опасен, скрывает конфликт
- Вариант C (warning) — усложняет API
- Вариант A — самый честный и простой: API возвращает граф "as-is"
- Клиент отображает оба факта, отсортированные по believability DESC
- Это доказывает ценность TruthFinder для post-MVP

---

## 3. SEED DATA FORMAT

**3.1. Формат:** Простой список URL (Вариант A)

**Реализация:**
```bash
# seed.txt
https://olgarozet.com/bio
https://bvshd.ru/teachers/rozet
https://linkedin.com/in/olgarozet
https://designmagazine.ru/interview-rozet-2023
```

**Скрипт:**
```python
# run_seed.py
for url in read_seed_txt():
    send_to_queue(url, authority=1.0)
```

**3.2. Кто собирает:** Координатор вручную (Google search за 1 час)

---

## 4. РАЗМЕР ГРАФА MVP

**Решение:** 30 узлов достаточно для демонстрации

**Обоснование:**
- Ценность MVP — в доказательстве трансформации "unstructured → structured"
- Демо-сценарий:
  1. Показать URL (статья)
  2. Показать Fact Nodes в Neo4j, извлечённые из этого URL
  3. Показать агрегацию Facts в канонический граф

Граф из 30 узлов, **полученный автономно** из 10 статей, ценнее для демо, чем 1000 узлов из CSV.

---

## 5. GRAPH API: CYPHER ENDPOINT

**Решение:** Cypher (Lambda endpoint), не GraphQL

**Обоснование:**
- Time to implement: 1 день vs 2-3 дня (AppSync)
- Гибкость (Demo): **Критична**. Во время демо возникнут вопросы, на которые GraphQL schema не ответит
- Аудитория: Координатор (технический) оценит гибкость Cypher
- GraphQL — продукт для потребителей (post-MVP)
- Cypher endpoint — инструмент для разработчика/аналитика (MVP)

---

## 6. DLQ WORKFLOW

**6.1. Как координатор видит DLQ:**
1. CloudWatch Alarm (DLQ > 0 messages)
2. SNS → Email координатору ("DLQ Alert: 3 messages waiting")
3. Координатор заходит в **AWS Console → SQS → DLQ**

**Никакого Admin UI в MVP.**

**6.2. Что делать с сообщениями:**
- **Transient error** (Claude API 503): AWS Console → "Redrive messages"
- **Permanent error** (malformed HTML): Удалить сообщение вручную

---

## 7. TEMPORAL NORMALIZATION

**Решение:** LLM-based normalization (обновлённая стратегия)

**Обоснование:**
- Simple heuristics — хрупкие
- Temporal parser — сложно
- Claude 3.5 отлично справляется с нормализацией дат in-context

**Обновлённая схема:**
```json
"temporal": {
  "start_raw": "в начале 2020-х",
  "end_raw": "несколько лет назад",
  "start_iso": "2020-01-01",  // LLM normalized
  "end_iso": "2023-12-31"      // LLM normalized
}
```

**LLM Prompt Instruction:**
> "В дополнение к _raw полям, попытайся нормализовать даты в ISO формат YYYY-MM-DD. Используй контекст статьи (если есть дата публикации). Если выражение слишком неоднозначно (e.g., 'давно'), оставь _iso поля как null."

**Lambda:** Просто доверяет _iso полям от LLM. Никакой сложной логики парсинга.

---

## 8. FREE TIER РЕАЛЬНОСТЬ

**Решение:** Migration plan НЕ нужен в MVP SOW

**Обоснование:**
- Лимит 50k узлов — огромен для персонального графа
- Даже при активном Snowballing достижение 50k займёт **годы** (высокий overlap контактов)
- Free tier покрывает: MVP + тестирование + первые 6-12 месяцев post-MVP
- Это не является риском для MVP

---

## ИТОГОВАЯ КОНФИГУРАЦИЯ MVP

```yaml
scope:
  - Core pipeline: Ingest → IE (Claude) → Graph (Neo4j)
  - Deterministic ER only
  - No TruthFinder (believability = LLM confidence)
  - No Snowballing
  - Cypher endpoint (not GraphQL)
  - Seed: 10-20 URLs

expected_output:
  graph_size: ~30 nodes, ~45 edges
  quality: "Грязный" граф (дубликаты, конфликты) - это feature, не bug
  demonstration: Доказательство трансформации unstructured → structured

timeline: 2-3 недели (1 senior engineer)

cost: $50-150/month
  - Claude API: $45
  - Neo4j Aura Free: $0
  - AWS Lambda/SQS/S3: ~$5

infrastructure:
  - AWS Lambda + SQS + S3 + Step Functions
  - Neo4j Aura (Free Tier)
  - Claude 3.5 Sonnet API

post_mvp_priorities:
  1. Probabilistic ER
  2. TruthFinder (self-consistency)
  3. Snowballing (BFS)
  4. GraphQL API
  5. Dashboard
```

---

## ГОТОВНОСТЬ К РЕАЛИЗАЦИИ

Все архитектурные, технические и практические вопросы решены.

**Следующий шаг:** Создание TASK_SOW.md — формализованного технического задания для инженера.

