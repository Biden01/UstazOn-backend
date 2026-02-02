"""
Lesson document generation service.

Generates structured lesson JSON composed of ordered blocks:
heading, theory, vocabulary, test (real DB entity), open_question.
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.teaching_materials import TeachingMaterial, MaterialType
from src.services.ai_service import ai_service

logger = logging.getLogger(__name__)


def _clean_ai_json(text: str) -> dict:
    """Strip markdown fences and parse JSON from AI response."""
    text = text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise


async def generate_lesson(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: str,
    topic: str,
    language: str = "kk",
    question_count: int = 10,
    difficulty: str = "medium",
    model: str = "gemini-2.5-flash",
) -> dict[str, Any]:
    """
    Generate a structured lesson document.

    Flow:
    1. AI generates theory, vocabulary, and open questions
    2. generate_and_save_test() creates a real Test entity in DB
    3. Assemble all blocks into the lesson JSON
    4. Save to TeachingMaterial table
    5. Return lesson id + full JSON
    """

    # --- Step 1: Generate lesson content via AI ---
    lang_instruction = (
        "Весь контент ДОЛЖЕН быть на казахском языке."
        if language == "kk"
        else "Весь контент ДОЛЖЕН быть на русском языке."
    )

    prompt = f"""Создай учебный материал (урок) по следующим параметрам:

Предмет: {subject}
Класс: {grade}
Тема: {topic}
Язык: {"казахский" if language == "kk" else "русский"}

{lang_instruction}

Верни ТОЛЬКО валидный JSON (без markdown, без текста до или после) в следующем формате:

{{
  "title": "Заголовок урока",
  "theory_sections": [
    {{
      "title": "Название раздела теории 1",
      "content": "Подробное объяснение теории. Минимум 3-4 абзаца текста."
    }},
    {{
      "title": "Название раздела теории 2",
      "content": "Подробное объяснение. Минимум 3-4 абзаца."
    }}
  ],
  "vocabulary": [
    {{
      "term": "Термин 1",
      "definition": "Определение термина 1"
    }},
    {{
      "term": "Термин 2",
      "definition": "Определение термина 2"
    }}
  ],
  "open_questions": [
    "Открытый вопрос для рефлексии 1?",
    "Открытый вопрос для рефлексии 2?",
    "Открытый вопрос для рефлексии 3?"
  ]
}}

Требования:
- Минимум 2 раздела теории с подробным содержанием
- Минимум 5 терминов в словаре
- Минимум 3 открытых вопроса
- Теория должна быть подробной и образовательной
- Словарь должен содержать ключевые термины по теме"""

    system_instruction = (
        "Ты - опытный учитель в казахстанской школе. "
        "Создавай подробные и качественные учебные материалы. "
        "Возвращай ТОЛЬКО валидный JSON без дополнительного текста."
    )

    result = await ai_service.chat(
        message=prompt,
        model=model,
        system_instruction=system_instruction,
    )

    ai_data = _clean_ai_json(result["text"])

    # --- Step 2: Generate test via existing service ---
    from src.services.test_service import generate_and_save_test

    test = await generate_and_save_test(
        db=db,
        user_id=user_id,
        subject=subject,
        grade=grade,
        topic=topic,
        question_count=question_count,
        difficulty=difficulty,
        model=model,
    )

    # --- Step 3: Assemble lesson JSON ---
    now = datetime.now(timezone.utc)

    lesson_title = ai_data.get("title", topic)

    blocks: list[dict[str, Any]] = []

    # Block 1: Heading
    blocks.append({
        "type": "heading",
        "level": 1,
        "text": lesson_title,
    })

    # Block 2: Theory sections
    theory_sections = ai_data.get("theory_sections", [])
    if theory_sections:
        blocks.append({
            "type": "theory",
            "sections": [
                {"title": s.get("title", ""), "content": s.get("content", "")}
                for s in theory_sections
            ],
        })

    # Block 3: Vocabulary
    vocabulary = ai_data.get("vocabulary", [])
    if vocabulary:
        blocks.append({
            "type": "vocabulary",
            "items": [
                {"term": v.get("term", ""), "definition": v.get("definition", "")}
                for v in vocabulary
            ],
        })

    # Block 4: Test (linked by ID)
    blocks.append({
        "type": "test",
        "test_id": test.id,
    })

    # Block 5: Open questions
    for q in ai_data.get("open_questions", []):
        blocks.append({
            "type": "open_question",
            "question": q,
        })

    lesson_content = {
        "meta": {
            "title": lesson_title,
            "subject": subject,
            "grade": grade,
            "topic": topic,
            "language": language,
            "created_at": now.isoformat(),
        },
        "layout": {
            "page_size": "A4",
            "font": "serif",
            "show_name_field": True,
            "show_date_field": True,
        },
        "blocks": blocks,
    }

    # --- Step 4: Save to DB ---
    material = TeachingMaterial(
        user_id=user_id,
        material_type=MaterialType.LESSON,
        title=lesson_title,
        subject=subject,
        grade=grade,
        topic=topic,
        content=lesson_content,
        ai_model=model,
        question_count=question_count,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    return {"id": material.id, "content": lesson_content}
