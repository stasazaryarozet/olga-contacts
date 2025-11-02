// Демо Cypher запросы для анализа графа

// 1. Все связи Ольги Розет (текущие и прошлые)
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(target)
RETURN 
    target.name as organization,
    f.type as relation_type,
    f.start_date as from_date,
    f.end_date as to_date,
    f.believability as confidence,
    f.context as evidence
ORDER BY f.believability DESC, f.start_date DESC;

// 2. Текущие места работы (end_date = null)
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(org:Organization)
WHERE f.end_date IS NULL AND f.type IN ["works_at", "taught_at"]
RETURN 
    org.name as current_organization,
    f.type as role,
    f.start_date as since,
    f.believability as confidence
ORDER BY f.start_date DESC;

// 3. Все со-кураторы и коллеги
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(person:Person)
WHERE f.type IN ["co_curated", "collaborated_with"]
RETURN 
    person.name as colleague,
    f.type as relation,
    f.context as context,
    f.believability as confidence
ORDER BY f.believability DESC;

// 4. Статистика графа
MATCH (n)
RETURN labels(n) as node_type, count(n) as count
ORDER BY count DESC;

// 5. Топ источников по количеству извлечённых фактов
MATCH (s:Source)-[:CLAIMS]->(f:Fact)
RETURN 
    s.url as source,
    s.authority as authority,
    count(f) as facts_count,
    s.last_processed as last_updated
ORDER BY facts_count DESC
LIMIT 10;

// 6. Факты с низкой уверенностью (для ревью)
MATCH (f:Fact)
WHERE f.believability < 0.90
RETURN 
    f.type as relation,
    f.context as evidence,
    f.believability as confidence
ORDER BY f.believability ASC
LIMIT 20;

// 7. Временная динамика (когда Ольга где работала)
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(org)
WHERE f.start_date IS NOT NULL
RETURN 
    org.name as organization,
    f.type as relation,
    f.start_date.year as year_started,
    CASE WHEN f.end_date IS NULL THEN "present" ELSE toString(f.end_date.year) END as year_ended
ORDER BY f.start_date DESC;

// 8. Все сущности, связанные с Ольгой (граф 1-го порядка)
MATCH (olga:Person {name: "Ольга Розет"})<-[:SUBJECT]-(f:Fact)-[:OBJECT]->(target)
RETURN DISTINCT 
    labels(target)[0] as entity_type,
    target.name as entity_name,
    count(f) as num_facts
ORDER BY num_facts DESC;

// 9. Конфликты (несколько фактов об одной связи с разными датами)
MATCH (subj)<-[:SUBJECT]-(f1:Fact)-[:OBJECT]->(obj)
MATCH (subj)<-[:SUBJECT]-(f2:Fact)-[:OBJECT]->(obj)
WHERE f1.type = f2.type 
  AND id(f1) < id(f2)
  AND (f1.end_date <> f2.end_date OR f1.start_date <> f2.start_date)
RETURN 
    subj.name as subject,
    obj.name as object,
    f1.type as relation,
    f1.start_date + " - " + f1.end_date as version1,
    f2.start_date + " - " + f2.end_date as version2,
    f1.believability as conf1,
    f2.believability as conf2
LIMIT 20;

// 10. Экспорт полного графа (для visualizations)
MATCH path = (s:Source)-[:CLAIMS]->(f:Fact)-[:SUBJECT|OBJECT]->(n)
RETURN path
LIMIT 1000;

