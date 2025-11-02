# Autonomous Contact Graph Builder

**Budget:** $0  
**Quality:** Confidence ≥ 0.85  
**Effort:** → 0 (after 1 hour setup)

Автономная система построения социального графа деловых контактов на базе Groq API (бесплатно) и Neo4j Desktop.

---

## Быстрый старт (1 час)

```bash
# 1. Setup
./setup.sh

# 2. Get Groq API key (FREE)
# Visit: https://console.groq.com
# Copy API key

# 3. Configure
cp .env.example .env
# Edit .env, add: GROQ_API_KEY=your_key_here

# 4. Install Neo4j Desktop
# Download from: https://neo4j.com/download/
# Create local database, set password: "contacts"
# Start database

# 5. Add seed URLs
nano config/seed.txt
# Add 10-20 URLs about Ольга Розет

# 6. Run
python3 src/main.py

# 7. Query results
# Open Neo4j Browser: http://localhost:7474
# Run queries from queries/demo_queries.cypher
```

---

## Архитектура

```
seed.txt (10-20 URLs)
  ↓
Python Script (main.py)
  ├─ Fetch HTML
  ├─ Extract text
  ├─ Groq API (Llama 3.1 70B) → NER + RE
  ├─ Entity Resolution (deterministic)
  └─ Neo4j (Fact Reification)
  
Neo4j Desktop (localhost:7687)
  ├─ (:Person), (:Organization) nodes
  ├─ (:Fact) nodes (reified relations)
  ├─ [:CLAIMS], [:SUBJECT], [:OBJECT] edges
  └─ Cypher queries for analysis
```

**Ключевые решения:**
- **Groq API:** Free tier Llama 3.1 70B (quality ~0.85-0.90)
- **Neo4j Desktop:** Free full-featured local instance
- **Fact Reification:** Поддержка multiple sources + confidence scoring
- **Deterministic ER:** Exact match только (MVP)

---

## Структура проекта

```
contacts/
├── src/
│   ├── main.py                 # Main script
│   ├── ie_pipeline.py          # Groq API integration
│   ├── entity_resolution.py    # Deterministic ER
│   ├── graph_db.py             # Neo4j driver
│   ├── prompts.py              # LLM prompts
│   └── utils.py                # Utilities
├── config/
│   ├── seed.txt                # Seed URLs (add yours)
│   └── .env.example            # Config template
├── queries/
│   └── demo_queries.cypher     # Demo Cypher queries
├── logs/
│   └── run.log                 # Auto-generated logs
├── requirements.txt
├── setup.sh                    # Setup script
├── .env                        # Your config (create from .env.example)
└── README.md                   # This file
```

---

## Dependencies

```
groq==0.11.0            # Groq API client
neo4j==5.15.0           # Neo4j driver
beautifulsoup4==4.12.2  # HTML parsing
requests==2.31.0        # HTTP client
python-dotenv==1.0.0    # Environment variables
lxml==4.9.3             # XML/HTML parser
```

Установка: `pip install -r requirements.txt`

---

## Configuration

### 1. Groq API Key

**Получение (бесплатно):**
1. Зайти на https://console.groq.com
2. Создать аккаунт (free)
3. Получить API key

**Настройка:**
```bash
echo "GROQ_API_KEY=gsk_your_key_here" >> .env
```

### 2. Neo4j Desktop

**Установка:**
1. Download: https://neo4j.com/download/
2. Install Neo4j Desktop (free)
3. Create new project "Contacts"
4. Create local database:
   - Name: contacts-graph
   - Password: contacts
   - Version: 5.x
5. Start database

**Проверка подключения:**
```bash
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'contacts'))
driver.verify_connectivity()
print('✓ Neo4j connected')
"
```

### 3. Seed URLs

Отредактировать `config/seed.txt`:
```
https://example.com/olga-rozet-bio
https://linkedin.com/in/olgarozet
https://design-magazine.ru/interview/rozet-2023
...
# Add 10-20 URLs total
```

**Где найти URLs:**
- Личный сайт/портфолио
- LinkedIn профиль
- Интервью в СМИ
- Страницы организаций (ВБШД, мастерская и т.д.)
- Статьи с упоминаниями

---

## Usage

### Однократный запуск

```bash
python3 src/main.py
```

**Output:**
```
🚀 Autonomous Contact Graph Builder v1.0
   Run started at 2025-11-01 22:30:00
============================================================
✓ Components initialized
📋 Found 15 seed URLs

[1/15] Processing: https://example.com/olga-bio
   Extracted 3,245 characters
   Source type: website_bio
   Extracted: 12 entities, 8 relations
   After ER: 11 canonical entities
   ✓ Stored 8 facts

...

============================================================
📊 Run Summary
============================================================
   URLs processed: 14/15
   Total facts stored: 67

📈 Database Stats:
   Person: 28 nodes
   Organization: 15 nodes
   Fact: 67 nodes
   Source: 15 nodes
   Relationships: 201

✓ Run completed at 2025-11-01 22:35:42
============================================================
```

### Автоматический запуск (cron)

```bash
# Edit crontab
crontab -e

# Add line (runs daily at 3am):
0 3 * * * cd /path/to/contacts && ./venv/bin/python src/main.py >> logs/cron.log 2>&1
```

---

## Queries

Открыть Neo4j Browser: http://localhost:7474

### Примеры запросов

**1. Все связи Ольги Розет:**
```cypher
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(target)
RETURN target.name, f.type, f.start_date, f.believability
ORDER BY f.believability DESC;
```

**2. Текущие места работы:**
```cypher
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(org)
WHERE f.end_date IS NULL AND f.type IN ["works_at", "taught_at"]
RETURN org.name, f.type, f.start_date;
```

**3. Со-кураторы:**
```cypher
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(person:Person)
WHERE f.type = "co_curated"
RETURN person.name, f.context, f.believability;
```

Больше queries: `queries/demo_queries.cypher`

---

## Troubleshooting

### "GROQ_API_KEY not found"
```bash
# Check .env exists
ls -la .env

# Check key is set
cat .env | grep GROQ_API_KEY

# If not, add it:
echo "GROQ_API_KEY=gsk_your_key" >> .env
```

### "Neo4j connection failed"
```bash
# Check Neo4j is running
# Open Neo4j Desktop, ensure database is started

# Check connection details in .env:
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=contacts
```

### "No relations extracted"
- Проверить quality seed URLs (есть ли там информация об Ольге?)
- Посмотреть logs/run.log для деталей
- Попробовать другие URLs

### "Rate limit exceeded"
- Groq free tier: ограничен по requests/minute
- Script автоматически делает exponential backoff
- Если проблема сохраняется: уменьшить число seed URLs или запускать реже

---

## Cost Breakdown

```yaml
groq_api:
  tier: Free
  model: Llama 3.1 70B
  limit: Достаточно для 20 docs/day
  cost: $0

neo4j:
  tier: Desktop (local, unlimited)
  cost: $0

compute:
  location: Local machine
  cost: $0

TOTAL: $0/month
```

---

## Quality Expectations

**Confidence scores:**
- ≥ 0.95: Высокая уверенность (LinkedIn, официальные bio)
- 0.85-0.95: Средняя уверенность (СМИ, интервью)
- 0.70-0.85: Низкая уверенность (косвенные упоминания)
- < 0.70: Отбрасывается системой

**Ожидаемое качество:**
- Precision: ~90% (мало false positives)
- Recall: ~70% (некоторые связи будут пропущены)
- Overall: Достаточно для демонстрации концепции

**Известные ограничения (MVP):**
- ❌ Нет Probabilistic ER → дубликаты узлов
- ❌ Нет TruthFinder → конфликты не разрешаются
- ❌ Нет Snowballing → граф ограничен seed URLs
- ✅ Deterministic ER → exact matches работают
- ✅ Fact Reification → готово к post-MVP улучшениям

---

## Next Steps (Post-MVP)

1. **Probabilistic Entity Resolution**
   - String similarity (Levenshtein)
   - Graph-based (GNN)
   - Confidence-based merging

2. **TruthFinder Algorithm**
   - Source authority scoring
   - Conflict resolution
   - Self-consistency

3. **Snowballing (BFS expansion)**
   - Auto-discovery новых sources
   - Query generation от extracted entities
   - Depth limiting

4. **Dashboard**
   - Web UI для monitoring
   - Visualizations
   - Manual review queue

---

## Documentation

- **[FINAL_ARCHITECTURE_GROQ.md](./FINAL_ARCHITECTURE_GROQ.md)** — Полная архитектура
- **[PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)** — История проектирования
- **[queries/demo_queries.cypher](./queries/demo_queries.cypher)** — Примеры Cypher queries

---

## Support

Вопросы? Проблемы? Проверьте:
1. `logs/run.log` для деталей
2. Neo4j Browser для состояния графа
3. `.env` для правильности конфигурации

---

**Версия:** 1.0  
**Дата:** 2025-11-01  
**Статус:** Production-ready MVP

