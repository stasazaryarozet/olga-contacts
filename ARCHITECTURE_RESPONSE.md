# АРХИТЕКТУРНОЕ РЕШЕНИЕ: Автономное построение социального графа

**Источник:** Ответ внешнего ИИ на запрос AI_PROMPT_CONTACT_BUILDER.md  
**Дата получения:** 2025-11-01  
**Статус:** Требует анализа и ответов на критические вопросы

---

## 1. АРХИТЕКТУРНОЕ РЕШЕНИЕ

### Паттерн преобразования: Event-Driven Probabilistic Graph Pipeline

**Ingestion (E):** Асинхронные, event-driven коннекторы для каждого источника (Web-hooks, IMAP IDLE, API-поллинг, Pub/Sub). Данные (включая delta) немедленно помещаются в отказоустойчивую очередь (Kafka/Pulsar) и архивируются в data lake (S3/GCS) для сохранения data provenance.

**Processing (T):** Потоковая обработка (Flink/Kafka Streams).
- **Content Extraction & Normalization:** Извлечение текста и метаданных (e.g., Tika).
- **Information Extraction (IE):** Применение SOTA Large Language Model (LLM) (локальный fine-tuned/quantized Llama/Mixtral или API-based GPT-4o/Claude 3 Opus) для:
  - **NER** (Person, Organization, Role, Event)
  - **Entity Linking** (связывание с известными сущностями, e.g., LinkedIn URL)
  - **Relation Extraction (RE)** (collaborated_on, works_at, met_at)
- **Confidence Scoring:** Каждая извлеченная сущность (V) и связь (E) получает вероятностную оценку (confidence score) от LLM.

**Loading & Maintenance (L):**
- **Graph Database:** Загрузка в Labeled Property Graph (LPG) (e.g., Neo4j, Neptune, TigerGraph).
- **Probabilistic Entity Resolution (ER):** Сущности не сливаются детерминированно. Вместо этого создаются "кандидатские" сущности. ER обрабатывается как фоновый (batch) процесс, использующий graph-native алгоритмы (e.g., Jaccard similarity на эмбеддингах + GNN) для вычисления probability_is_match между узлами. Слияние происходит автономно только при p > 0.99.
- **Graph Serving:** API (GraphQL или Cypher) для доступа к графу G.

### Выбор технологий (SOTA Justification)

| Компонент | Технология | Обоснование |
|-----------|-----------|-------------|
| **Ingestion** | Kafka/Pulsar | Необходимы для self-scheduling и self-healing (через replayability). Гарантируют доставку и разделяют ingest-слой от processing-слоя. |
| **IE (NER/RE)** | LLM (Transformer-based) | Единственный SOTA-подход для zero-shot и few-shot RE в сложных, неструктурированных доменах, что является требованием при Effort → 0 (нет данных для fine-tuning). |
| **Processing** | Flink | SOTA-движок для stateful stream processing. Необходим для инкрементальных обновлений графа и управления сложным состоянием (e.g., "какие email уже обработаны"). |
| **Graph DB** | Neo4j/TigerGraph (LPG) | LPG — нативная модель для G = (V, E) с Properties (e.g., Role, Confidence). Оптимальны для запросов на "связность" (e.g., "с кем Ольга работала в 2023?"). |
| **Orchestration** | Kubernetes + KEDA/Argo Events | Self-healing на уровне инфраструктуры. Self-scheduling через event-driven масштабирование (e.g., новый email → запуск IE pod). |

### Стратегия автоматизации (No-Supervision)

1. **Idempotency:** Весь pipeline должен быть идемпотентным. Повторная обработка источника (e.g., self-healing после сбоя) не должна создавать дубликаты V или E.

2. **Autonomous ER:** Entity Resolution (слияние "John Smith" и "J. Smith") — главная точка отказа для Effort → 0. Решение: не сливать принудительно. Система хранит G как probabilistic graph. Запросы к G возвращают результаты с учетом вероятностей совпадения.

3. **Continuous Learning (Self-Consistency):** Система использует G как RAG-контекст для самой себя. Если новые данные (Источник Б) противоречат существующей связи (Источник А), система снижает confidence этой связи. Если данные подтверждаются, confidence растет. Это self-correction без HITL (Human-in-the-Loop).

4. **Anomaly Detection:** Автономный агент мониторит топологию G. Обнаружение аномалий (e.g., "supernode" с 1000+ связями works_at, резкое изменение graph density) триггерит self-healing (e.g., принудительный re-processing затронутых V).

### Управление рисками

**Технические:**
- **Риск:** Семантический дрейф (модель RE устарела). **Мит.:** Использование Foundation Model APIs (SOTA 'by default') или self-consistency (см. выше) для down-weighting старых, неконсистентных данных.
- **Риск:** Ошибка ER (слияние двух разных людей). **Мит.:** Probabilistic ER. Никогда не сливать безвозвратно. Приоритет Precision над Recall.

**Юридические (Compliance):**
- **Риск:** Обработка PII (личная почта, контакты) нарушает GDPR/CCPA. **Мит.:** Privacy-by-Design:
  1. **Data Provenance:** Каждое V и E обязано иметь ссылку на источник (ID письма, URL).
  2. **Right to be Forgotten:** Запрос на удаление должен каскадно удалять все V и E, исключительно полученные из этого источника.
  3. **Минимизация:** Pipeline работает в trusted environment (e.g., VPC или on-premise).

**Этические:**
- **Риск:** Модель "галлюцинирует" (создает ложные) связи. **Мит.:** Thresholding. В G загружаются только E с confidence > 0.9 (настраиваемый параметр). Ложные E (низкая confidence) отбрасываются.

---

## 2. КРИТИЧЕСКИЕ ВОПРОСЫ

### Вопрос 1: Доступ и Легальность (Приватные Источники)
Каков юридический и технический механизм доступа к приватным источникам (почта, контакты)? Получено ли явное, granular (поконтентное) согласие Ольги на обработку? (Например, для GDPR, простого "Да" недостаточно).

### Вопрос 2: Приоритет Ошибок (Precision vs. Recall)
В системе без надзора ошибки неизбежны. Что является катастрофической ошибкой:
- **A) False Positive:** Система добавила неверную связь (e.g., "Ольга — клиент X", хотя это не так).
- **B) False Negative:** Система пропустила реальную связь.

(Выбор A или B фундаментально меняет confidence thresholds и агрессивность ER).

### Вопрос 3: Проблема "Холодного Старта" (Bootstrap)
Effort → 0 означает zero-shot или few-shot learning. Как система должна распознавать доменно-специфичные связи (e.g., "куратор выставки", "участник резиденции")?
- Приемлемо ли использовать LLM-generated synthetic data для fine-tuning модели RE?
- Или система должна работать только в режиме Open Relation Extraction (OIE), извлекая любые тройки (Субъект, Предикат, Объект)?

### Вопрос 4: Инфраструктура и Затраты
Каковы ограничения на TCO (Total Cost of Ownership)?
- Система будет развернута on-premise / private cloud (требует локальных GPU, но privacy-safe)?
- Или в public cloud (требует оплаты per-API-call к LLM, но SOTA "из коробки")?

### Вопрос 5: Темпоральность и Контекст
Граф G должен быть статическим или темпоральным?
- Достаточно ли E = (Olga, works_at, Acme)?
- Или требуется E = (Olga, works_at, Acme, start=2020, end=2022, source=email_id_123)? (Второе экспоненциально усложняет RE и ER).

### Вопрос 6: Определение "Контакта"
Каков порог relevance? Если Ольга получила spam-email от "CEO X", является ли "CEO X" узлом V в ее графе? (Требуется context-aware filtering на уровне IE).

---

## СТАТУС

**Следующий шаг:** Ответить на критические вопросы для финализации архитектуры.

