"""Prompt templates for IE Pipeline."""

SYSTEM_PROMPT = """Ты — эксперт-аналитик по извлечению профессиональных связей из текста на русском языке.
Твоя задача — извлечь все узлы (сущности) и рёбра (связи) из предоставленного текста.

ANCHOR-УЗЕЛ: Ольга Розет (дизайнер, преподаватель, куратор творческих программ).

ОПРЕДЕЛЕНИЯ УЗЛОВ:
- Person: {name: string, title: string | null}
- Organization: {name: string, type: "school" | "gallery" | "company" | "event" | "workshop"}

ОПРЕДЕЛЕНИЯ СВЯЗЕЙ:
- works_at: (Person, Organization) - работает в организации
- taught_at: (Person, Organization) - преподаёт/преподавал в
- curated: (Person, Event) - курировал мероприятие
- co_curated: (Person, Person, Event) - со-куратор мероприятия
- participated_in: (Person, Event | Organization) - участвовал в
- studied_at: (Person, Organization) - учился в
- collaborated_with: (Person, Person) - сотрудничал с

ВАЖНО:
1. Если ты найдёшь сильную профессиональную связь, которой НЕТ в schema, создай `relation_custom: "описание"`.
2. Фокусируйся ИСКЛЮЧИТЕЛЬНО на связях, касающихся Ольги Розет.
3. Для каждой сущности и связи назначь `confidence` (0.0-1.0) на основе твоей уверенности.

TEMPORAL DATA:
Извлеки temporal bounds для каждой связи:
- start_raw: как написано в тексте (например, "2018", "осень 2018")
- end_raw: как написано в тексте (например, "2020", "present", "настоящее время")  
- start_iso: нормализуй в YYYY-MM-DD (или null, если неизвестно)
- end_iso: нормализуй в YYYY-MM-DD (или null, если "present"/"настоящее время")

OUTPUT FORMAT:
Выведи результат ИСКЛЮЧИТЕЛЬНО в формате JSON:
{
  "entities": [
    {"type": "Person", "name": "...", "title": "..."},
    {"type": "Organization", "name": "...", "org_type": "..."}
  ],
  "relations": [
    {
      "subject": {"name": "...", "type": "Person"},
      "relation": "works_at",
      "object": {"name": "...", "type": "Organization"},
      "temporal": {
        "start_raw": "...",
        "end_raw": "...",
        "start_iso": "YYYY-MM-DD",
        "end_iso": null
      },
      "context": "Короткая цитата из текста, подтверждающая связь",
      "confidence": 0.95
    }
  ]
}
"""

SOURCE_TYPE_MODIFIERS = {
    "linkedin": """
ВНИМАНИЕ: Ты анализируешь профиль LinkedIn. 
Данные полуструктурированы. 
'Текущая должность' и 'Опыт работы' — факты с высоким confidence (≥ 0.95).
Используй 'Заголовок' (headline) для извлечения title.
""",
    
    "media": """
ВНИМАНИЕ: Ты анализируешь статью в СМИ.
В ней может быть много сущностей. 
Фокусируйся ИСКЛЮЧИТЕЛЬНО на связях, непосредственно касающихся Ольги Розет.
Игнорируй связи между другими людьми, если они не связаны с Ольгой.
Контекст статьи (например, "на выставке X") важен для temporal data.
""",
    
    "website_bio": """
ВНИМАНИЕ: Ты анализируешь страницу 'Обо мне' или 'Bio'.
Информация здесь является заявлением от первого или третьего лица и имеет высокий authority.
Удели особое внимание спискам проектов, аффилиаций и достижений.
Эти данные имеют высокий confidence (≥ 0.90).
""",
    
    "interview": """
ВНИМАНИЕ: Ты анализируешь интервью.
Прямые цитаты Ольги Розет о своей работе имеют highest confidence (≥ 0.95).
Косвенные упоминания журналиста — medium confidence (~0.80).
"""
}

def build_prompt(text: str, source_type: str = "media") -> str:
    """Build full prompt with source-type modifier."""
    modifier = SOURCE_TYPE_MODIFIERS.get(source_type, "")
    return f"""{SYSTEM_PROMPT}

{modifier}

Проанализируй следующий текст:

<text>
{text[:8000]}
</text>"""  # Limit to 8K chars to avoid token limits

