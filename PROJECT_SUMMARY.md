# СВОДКА: Проект "Контакты" — Завершение проектирования

**Дата:** 2025-11-01  
**Статус:** ✅ Проектирование завершено. Готово к реализации.

---

## ЧТО БЫЛО СДЕЛАНО

### 1. Диалог с Gemini (через веб)

**Раунд 1: Исходный запрос**
- Создан [AI_PROMPT_CONTACT_BUILDER.md](./AI_PROMPT_CONTACT_BUILDER.md) — запрос максимального мета-уровня
- Получена полная архитектура: Event-Driven Probabilistic Graph Pipeline
- Сохранено в [ARCHITECTURE_RESPONSE.md](./ARCHITECTURE_RESPONSE.md)

**Раунд 2: 7 критических вопросов**
- Русский язык + креативный домен
- API vs Self-hosted LLM
- Seed data strategy
- Entity Resolution пороги
- Self-consistency алгоритм
- MVP vs Enterprise архитектура
- Success metrics

Ответы сохранены в [GEMINI_RESPONSES.md](./GEMINI_RESPONSES.md)

**Раунд 3: 8 вопросов уровня реализации**
- Промпт-стратегия (source-aware)
- Query generation для snowballing
- Source Authority инициализация
- Temporal extraction
- TruthFinder storage в Neo4j
- MVP scope детализация
- Cost breakdown
- Error handling

Ответы сохранены в [GEMINI_RESPONSES.md](./GEMINI_RESPONSES.md)

**Раунд 4: 8 вопросов практичности MVP**
- MVP без Probabilistic ER — приемлемо?
- MVP без TruthFinder — как обрабатывать конфликты?
- Seed data format
- Минимальный размер графа для демо
- GraphQL vs Cypher
- DLQ workflow
- Temporal parser
- Free tier limits

Финальные решения в [GEMINI_FINAL_ANSWERS.md](./GEMINI_FINAL_ANSWERS.md)

---

## ИТОГОВЫЙ DELIVERABLE

### ⭐ [TASK_SOW.md](./TASK_SOW.md) — Техническое Задание для реализации MVP

**Содержит:**
1. Цель проекта и критерии успеха
2. Полная архитектура (диаграммы + компоненты)
3. Технические требования:
   - IE Pipeline (Claude 3.5 Sonnet + source-aware prompting)
   - Deterministic Entity Resolution
   - Neo4j Fact Reification schema
   - Cypher API endpoint
4. Scope MVP (что включено / не включено)
5. Структура кода (репозиторий)
6. Acceptance criteria (функциональные + нефункциональные)
7. Cost estimate (<$5/month для MVP)
8. Риски и mitigation
9. Post-MVP roadmap

**Timeline:** 2-3 недели (1 senior engineer)  
**Budget:** < $150/month (production), < $5/month (MVP testing)

---

## КЛЮЧЕВЫЕ АРХИТЕКТУРНЫЕ РЕШЕНИЯ

### Stack (MVP)
- **LLM:** Claude 3.5 Sonnet API (SOTA для русского языка + креативный домен)
- **Infrastructure:** AWS Lambda + SQS + S3 + Step Functions (serverless)
- **Graph DB:** Neo4j Aura Free Tier
- **API:** Cypher endpoint (гибкость для демо)

### Trade-offs MVP
- ❌ Без Probabilistic ER → граф будет содержать дубликаты (фича для демо)
- ❌ Без TruthFinder → конфликты не разрешаются (API возвращает все)
- ❌ Без Snowballing → граф из 30 узлов (достаточно для proof-of-concept)
- ✅ Deterministic ER only (exact match email/linkedin/name+org)
- ✅ LLM-based temporal normalization (без сложного parser)
- ✅ Fact Reification в Neo4j (поддержка TruthFinder в будущем)

### Ожидаемый результат MVP
- Обработка 10-20 seed URLs автономно
- Граф: ~30 persons/orgs, ~45 facts
- Демонстрация: "unstructured text → structured graph"
- Cost: < $1 за полный run (20 URLs)

---

## ДОКУМЕНТАЦИЯ ПРОЕКТА

### Навигация
1. **[AI_PROMPT_CONTACT_BUILDER.md](./AI_PROMPT_CONTACT_BUILDER.md)** — Исходный запрос к Gemini
2. **[ARCHITECTURE_RESPONSE.md](./ARCHITECTURE_RESPONSE.md)** — Полная архитектура + 6 критических вопросов
3. **[QUESTIONS_TO_GEMINI.md](./QUESTIONS_TO_GEMINI.md)** — 7 вопросов для уточнения
4. **[GEMINI_RESPONSES.md](./GEMINI_RESPONSES.md)** — Детальные ответы (модели, алгоритмы, технологии)
5. **[FOLLOWUP_QUESTIONS_TO_GEMINI.md](./FOLLOWUP_QUESTIONS_TO_GEMINI.md)** — 8 вопросов реализации
6. **[FINAL_PRACTICALITY_QUESTIONS.md](./FINAL_PRACTICALITY_QUESTIONS.md)** — 8 вопросов практичности
7. **[GEMINI_FINAL_ANSWERS.md](./GEMINI_FINAL_ANSWERS.md)** — Финальные решения MVP
8. **[TASK_SOW.md](./TASK_SOW.md)** ⭐ — **ГЛАВНЫЙ ДОКУМЕНТ** для реализации

### README
[README.md](./README.md) обновлён:
- Быстрый старт для инженера
- Краткое описание архитектуры
- Полная навигация по документации
- Старая архитектура от Gemini (октябрь) перенесена в collapsed section

---

## NEXT STEPS

### Для реализации:
1. Читать **[TASK_SOW.md](./TASK_SOW.md)**
2. Setup AWS infrastructure (Terraform/CDK)
3. Implement IE pipeline (Lambda + Claude API)
4. Implement Graph Loader (Lambda + Neo4j)
5. Create seed.txt (10-20 URLs, 1 hour effort)
6. Run & demo

### Для согласования (опционально):
- Подтвердить budget (~$150/month production)
- Подтвердить timeline (2-3 недели)
- Подтвердить приоритет Precision > Recall

---

## ФИЛОСОФИЯ ПРОЕКТА

**Effort → 0:** Система работает автономно после инициализации (1 hour seed data)

**MVP = Proof of Concept:** Демонстрация трансформации, не идеальный граф

**"Грязный" граф — это фича:** Дубликаты и конфликты доказывают необходимость post-MVP

**SOTA без compromises:** Claude 3.5 Sonnet, Neo4j, serverless AWS

---

Проект готов к передаче инженеру для реализации.

