# ВОПРОС К GEMINI: Оптимальная локальная LLM для данного железа

**Дата:** 2025-11-01  
**Контекст:** Budget = 0, локальная LLM разрешена

---

## ХАРАКТЕРИСТИКИ СИСТЕМЫ

```yaml
computer:
  ram: 16 GB
  cpu: Intel i7-7920HQ (8 cores, 3.10 GHz)
  gpu: Radeon Pro 560 (4GB VRAM) + Intel HD 630
  metal: Metal 3 support
  os: macOS 12.6 (Monterey)
  architecture: x86_64 (не Apple Silicon)
```

---

## ТРЕБОВАНИЯ

```yaml
budget: 0 рублей
task: NER + Relation Extraction (русский язык + креативный домен)
quality_target: confidence ≥ 0.85-0.90 (minimum acceptable)
throughput: 10-20 documents на запуск, раз в день/неделю
effort: → 0 (автономная работа после setup)
```

---

## ВОПРОСЫ

### 1. Оптимальная модель для этого железа

**Варианты:**
- Llama 3.1 8B (quantized Q4/Q5)
- Llama 3.1 7B
- Mixtral 8x7B (quantized)
- Phi-3 Medium (14B)
- Qwen 2.5 (14B)
- DeepSeek V2 Lite
- Другое?

**Для каждого кандидата:**
- Поместится ли в 16GB RAM при quantization Q4/Q5?
- Какая скорость inference на CPU i7-7920HQ? (tokens/sec)
- Можно ли использовать GPU (Radeon Pro 560, 4GB VRAM) для ускорения?
- **Ключевой вопрос:** Какое качество NER/RE на русском языке для креативного домена?

### 2. Framework для запуска

**Варианты:**
- Ollama (самый простой, но оптимален ли?)
- llama.cpp (больше контроля, сложнее)
- MLX (только для Apple Silicon, не подходит)
- LM Studio (GUI, но можно ли автоматизировать?)

Какой framework рекомендуешь для **автономной работы** (cron job) на этом железе?

### 3. Quantization strategy

Для модели размером X (e.g., 8B parameters):
- **Q4_K_M:** ~4.5 GB RAM, скорость high, качество medium
- **Q5_K_M:** ~5.5 GB RAM, скорость medium, качество higher
- **Q8:** ~8 GB RAM, скорость low, качество highest

Какая quantization оптимальна для:
- Баланс скорости и качества NER/RE?
- Уместиться в 16GB RAM с запасом (OS + другие процессы занимают ~4-6 GB)?

### 4. Реалистичная оценка качества

**Критический вопрос:**
При использовании оптимальной локальной модели на этом железе, какой **реальный confidence** можно ожидать для задачи NER + RE (русский, креативный домен)?

- Llama 3.1 8B Q5: confidence ≈ ?
- Mixtral 8x7B Q4: confidence ≈ ?
- Phi-3 Medium Q5: confidence ≈ ?

Сравнение с Claude 3.5 Sonnet (который давал ~0.95):
- Локальная модель даст ~0.85? ~0.75? ~0.65?

### 5. Альтернатива: Бесплатные Cloud API

Может быть, при budget = 0 эффективнее использовать:
- **Google Gemini 1.5 Flash** (free tier: 1500 req/day)
- Качество близко к Claude?
- Стабильность free tier?

**Trade-off:**
- Локальная LLM: 100% автономность, но качество ниже
- Gemini Free API: качество выше, но зависимость от Google

Какой подход рекомендуешь при budget = 0?

### 6. Практическая архитектура

Если выбрана локальная LLM, опиши конкретную архитектуру:

```python
# Псевдокод
Ollama running (daemon) на localhost:11434
Python script (cron: раз в день):
  1. Read seed URLs from config
  2. Fetch HTML
  3. Call Ollama API (localhost) для NER/RE
  4. Deterministic ER
  5. Save to SQLite (или Neo4j Desktop, бесплатно)
  6. Log results
```

**Вопросы:**
- Сколько времени займёт обработка 20 URLs на этом железе?
- Будет ли компьютер "тормозить" во время inference?
- Можно ли запускать процесс в background без блокировки системы?

---

## ИТОГО

Нужен **конкретный, реализуемый план** для:
1. Модель (какая именно + quantization)
2. Framework (Ollama / llama.cpp / другое)
3. Ожидаемое качество (honest assessment)
4. Timeline inference (сколько займёт 20 documents?)
5. Architecture (Python script structure)

Цель: **Максимальное качество при budget = 0 на этом конкретном железе**.

