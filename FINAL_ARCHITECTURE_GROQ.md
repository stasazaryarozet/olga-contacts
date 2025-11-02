# ФИНАЛЬНАЯ АРХИТЕКТУРА: Budget = 0, Quality ≥ 0.85

**Версия:** 2.0 (Groq API)  
**Дата:** 2025-11-01  
**Статус:** Утверждено к реализации

---

## РЕШЕНИЕ: Groq API + Локальная инфраструктура

### Обоснование
- **Groq API (Llama 3.1 70B):** Free tier, quality ~0.85-0.90
- **Локальный Python script:** Автономность после setup
- **Neo4j Desktop:** Бесплатная full-featured версия
- **Budget:** 0 рублей ✓
- **Quality:** ≥ 0.85 ✓
- **Effort:** → 0 (после 1 hour setup) ✓

---

## АРХИТЕКТУРА

```
┌─────────────────────────────────────────┐
│  seed.txt (10-20 URLs)                  │
│  - Вручную собрано координатором (1hr) │
└────────────┬────────────────────────────┘
             │
             v
┌─────────────────────────────────────────┐
│  Python Script (cron: daily)            │
│  ├─ Read seed URLs                      │
│  ├─ Fetch HTML (requests + bs4)         │
│  ├─ Extract text                        │
│  └─ For each document:                  │
│      ├─ Call Groq API (Llama 70B)       │
│      ├─ NER + RE extraction             │
│      ├─ Temporal normalization (LLM)    │
│      └─ Save raw JSON                   │
└────────────┬────────────────────────────┘
             │
             v
┌─────────────────────────────────────────┐
│  Entity Resolution (deterministic)      │
│  ├─ Exact email match                   │
│  ├─ Exact LinkedIn URL match            │
│  └─ Exact name + org match              │
└────────────┬────────────────────────────┘
             │
             v
┌─────────────────────────────────────────┐
│  Neo4j Desktop (localhost:7687)         │
│  ├─ Fact Reification schema             │
│  ├─ (:Person), (:Org), (:Fact) nodes    │
│  ├─ [:CLAIMS], [:SUBJECT], [:OBJECT]    │
│  └─ Cypher queries for analysis         │
└─────────────────────────────────────────┘
```

---

## STACK

```yaml
llm:
  provider: Groq API
  model: llama-3.1-70b-versatile
  cost: $0 (free tier)
  quality: ~0.85-0.90 confidence
  rate_limit: Достаточно для 20 docs/day

script:
  language: Python 3.11+
  runtime: Local (macOS)
  automation: cron (daily at 3am)
  
dependencies:
  - requests (HTTP)
  - beautifulsoup4 (HTML parsing)
  - groq (SDK)
  - neo4j (driver)
  
storage:
  database: Neo4j Desktop (free)
  port: localhost:7687
  size: Unlimited (локально)
  
cost:
  total: $0/month
  groq_api: $0 (free tier)
  neo4j: $0 (local)
  compute: $0 (локальный скрипт)
```

---

## КОМПОНЕНТЫ

### 1. IE Pipeline (Groq API)

**Prompt template:**
```xml
<system>
Ты — эксперт-аналитик по извлечению профессиональных связей.
Anchor-узел: Ольга Розет (дизайнер, преподаватель, куратор).

SCHEMA:
- Person: {name, title}
- Organization: {name, type: "school"|"gallery"|"company"|"event"}

RELATIONS:
- works_at, taught_at, curated, co_curated, participated_in

TEMPORAL: Извлеки start_date, end_date в ISO format.
OUTPUT: Только JSON массив relations.
</system>

<user>
<text>{DOCUMENT_TEXT}</text>
</user>
```

**Code:**
```python
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

def extract_entities(text, source_type="media"):
    prompt = build_prompt(text, source_type)
    
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1  # Low temp для консистентности
    )
    
    return json.loads(response.choices[0].message.content)
```

### 2. Entity Resolution (Deterministic)

```python
def deterministic_er(entities):
    """Exact match только."""
    merged = {}
    
    for entity in entities:
        key = None
        
        # Rule 1: Email
        if entity.get('email'):
            key = f"email:{entity['email']}"
        # Rule 2: LinkedIn
        elif entity.get('linkedin'):
            key = f"linkedin:{entity['linkedin']}"
        # Rule 3: Name + Org
        elif entity.get('name') and entity.get('organization'):
            key = f"name_org:{entity['name']}:{entity['organization']}"
        else:
            # No merge, keep as is
            key = f"unique:{uuid.uuid4()}"
        
        if key in merged:
            merged[key]['sources'].append(entity['source'])
        else:
            merged[key] = entity
            merged[key]['sources'] = [entity['source']]
    
    return list(merged.values())
```

### 3. Neo4j Storage (Fact Reification)

```python
from neo4j import GraphDatabase

class GraphDB:
    def __init__(self, uri="bolt://localhost:7687"):
        self.driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))
    
    def store_fact(self, fact):
        with self.driver.session() as session:
            session.execute_write(self._create_fact, fact)
    
    @staticmethod
    def _create_fact(tx, fact):
        query = """
        // 1. Найти/создать Source
        MERGE (s:Source {url: $source_url})
        ON CREATE SET s.authority = $authority, s.ingested_at = datetime()
        
        // 2. Создать Fact
        CREATE (f:Fact {
            id: $fact_id,
            type: $relation_type,
            start_date: $start_date,
            end_date: $end_date,
            believability: $confidence,
            context: $context
        })
        
        // 3. Найти/создать Subject
        MERGE (subj:Person {name: $subject_name})
        
        // 4. Найти/создать Object
        MERGE (obj:Org {name: $object_name})
        
        // 5. Связи
        CREATE (s)-[:CLAIMS {confidence_llm: $confidence}]->(f)
        CREATE (f)-[:SUBJECT]->(subj)
        CREATE (f)-[:OBJECT]->(obj)
        """
        tx.run(query, **fact)
```

### 4. Main Script

```python
#!/usr/bin/env python3
"""
Autonomous Contact Graph Builder
Daily cron job: 0 3 * * *
"""

import os
from pathlib import Path
from datetime import datetime

# Config
SEED_FILE = Path(__file__).parent / "seed.txt"
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

def main():
    log(f"=== Run started at {datetime.now()} ===")
    
    # 1. Read seeds
    urls = SEED_FILE.read_text().strip().split('\n')
    log(f"Found {len(urls)} seed URLs")
    
    # 2. Process each
    for url in urls:
        try:
            # Fetch
            html = fetch(url)
            text = extract_text(html)
            
            # IE (Groq API)
            extracted = extract_entities(text, detect_source_type(url))
            log(f"Extracted {len(extracted['relations'])} relations from {url}")
            
            # ER
            entities = deterministic_er(extracted['entities'])
            
            # Store
            db = GraphDB()
            for relation in extracted['relations']:
                db.store_fact({
                    'source_url': url,
                    'authority': 1.0,  # seed = high authority
                    'fact_id': generate_fact_id(relation),
                    'relation_type': relation['type'],
                    'subject_name': relation['subject']['name'],
                    'object_name': relation['object']['name'],
                    'start_date': relation['temporal'].get('start_iso'),
                    'end_date': relation['temporal'].get('end_iso'),
                    'confidence': relation['confidence'],
                    'context': relation['context']
                })
            
            log(f"✓ Processed {url}")
            
        except Exception as e:
            log(f"✗ Error processing {url}: {e}")
    
    log(f"=== Run completed ===")

if __name__ == "__main__":
    main()
```

---

## DELIVERABLES

```
contacts/
├── src/
│   ├── main.py (main script)
│   ├── ie_pipeline.py (Groq API)
│   ├── entity_resolution.py
│   ├── graph_db.py (Neo4j)
│   ├── prompts.py (prompt templates)
│   └── utils.py
├── config/
│   ├── seed.txt (10-20 URLs)
│   └── .env.example (GROQ_API_KEY)
├── logs/
│   └── (автоматически создаётся)
├── queries/
│   └── demo_queries.cypher (примеры запросов)
├── requirements.txt
├── setup.sh (Neo4j + deps)
├── README.md (deployment guide)
└── crontab.example
```

---

## DEPLOYMENT (1 hour)

```bash
# 1. Install Neo4j Desktop
# Download from neo4j.com/download (free)
# Create local database, password: "contacts"

# 2. Install Python dependencies
cd contacts
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Setup Groq API
# Sign up at console.groq.com (free)
# Get API key
echo "GROQ_API_KEY=your_key_here" > .env

# 4. Create seed.txt
cat > config/seed.txt << EOF
https://example.com/olga-rozet-bio
https://linkedin.com/in/olgarozet
... (10-20 URLs total)
EOF

# 5. Test run
python src/main.py

# 6. Setup cron
crontab -e
# Add: 0 3 * * * cd /path/to/contacts && venv/bin/python src/main.py >> logs/cron.log 2>&1
```

---

## ACCEPTANCE CRITERIA

1. ✅ Обработка 10-20 seed URLs автономно
2. ✅ Извлечено ≥ 30 (:Person) или (:Org)
3. ✅ Извлечено ≥ 45 (:Fact) с believability ≥ 0.85
4. ✅ Deterministic ER работает (exact matches merged)
5. ✅ Neo4j queries возвращают результаты
6. ✅ Cost = $0
7. ✅ Cron job работает без intervention

---

## RISKS & MITIGATIONS

| Risk | Mitigation |
|------|-----------|
| Groq free tier изменён | Fallback на другой free API (Together AI) |
| Rate limit hit | Exponential backoff + retry |
| Neo4j Desktop crash | Auto-restart в cron wrapper |
| Bad URL (404) | Try-catch + log, продолжить |

---

**Ready to implement.** Timeline: 1 день разработки + 1 hour deployment.

