"""
AI QMJ (Қысқа мерзімді жоспар) generation service.

Generates structured QMJ JSON following the real Kazakhstan
short-term lesson plan format and saves to TeachingMaterial table.
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


async def generate_qmj(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: str,
    topic: str,
    language: str = "kk",
    model: str = "gemini-2.5-flash",
) -> dict[str, Any]:
    """
    Generate a structured QMJ (short-term lesson plan) using AI.

    The output follows the official Kazakhstan QMJ format:
    - lesson_info with objectives and assessment criteria
    - stages (beginning, middle, end) with teacher/student activities
    - differentiation
    - reflection

    Returns {"id": <TeachingMaterial.id>, "content": <structured JSON>}
    """

    lang_label = "казахском" if language == "kk" else "русском"
    lang_instruction = (
        "Весь контент ДОЛЖЕН быть на казахском языке (қазақ тілінде)."
        if language == "kk"
        else "Весь контент ДОЛЖЕН быть на русском языке."
    )

    prompt = f"""Создай ҚМЖ (Қысқа мерзімді жоспар / Краткосрочный план урока) по следующим параметрам:

Предмет: {subject}
Класс: {grade}
Тема урока: {topic}
Язык: {lang_label}

{lang_instruction}

Верни ТОЛЬКО валидный JSON (без markdown, без текста до или после) в следующем формате:

{{
  "lesson_info": {{
    "subject": "{subject}",
    "topic": "{topic}",
    "grade": "{grade}",
    "duration": 40,
    "learning_objectives": [
      "Оқу мақсаты / Цель обучения 1 (код из учебной программы, если известен)",
      "Оқу мақсаты / Цель обучения 2"
    ],
    "lesson_objectives": [
      "Сабақ мақсаты / Цель урока 1 — что ученики смогут делать к концу урока",
      "Сабақ мақсаты / Цель урока 2"
    ],
    "assessment_criteria": [
      "Бағалау критерийі / Критерий оценивания 1",
      "Бағалау критерийі / Критерий оценивания 2"
    ],
    "values": "Құндылықтар / Привитие ценностей — какие ценности прививаются через урок",
    "cross_curricular_links": "Пәнаралық байланыс / Межпредметные связи",
    "prior_knowledge": "Алдыңғы білім / Предшествующие знания — что ученики уже должны знать",
    "resources": [
      "Ресурс 1 (учебник, раздаточный материал и т.д.)",
      "Ресурс 2"
    ]
  }},
  "stages": [
    {{
      "name": "Сабақтың басы",
      "name_ru": "Начало урока",
      "duration": 5,
      "teacher_activities": "Подробное описание действий учителя на данном этапе: приветствие, мотивация, создание проблемной ситуации, объявление темы и целей урока",
      "student_activities": "Подробное описание действий учеников: отвечают на вопросы, участвуют в обсуждении, формулируют тему",
      "assessment": "Формативное оценивание / Наблюдение / Устная обратная связь",
      "resources": "Используемые ресурсы на данном этапе"
    }},
    {{
      "name": "Сабақтың ортасы",
      "name_ru": "Середина урока",
      "duration": 30,
      "teacher_activities": "Подробное описание действий учителя: объяснение нового материала, организация работы в группах/парах, демонстрация примеров, руководство практической работой. Минимум 3-4 предложения с конкретными заданиями и методами.",
      "student_activities": "Подробное описание действий учеников: слушают, записывают, выполняют задания, работают в группах, обсуждают, презентуют результаты. Минимум 3-4 предложения.",
      "assessment": "Формативное оценивание: взаимооценивание, самооценивание, критериальное оценивание, наблюдение учителя",
      "resources": "Используемые ресурсы"
    }},
    {{
      "name": "Сабақтың соңы",
      "name_ru": "Конец урока",
      "duration": 5,
      "teacher_activities": "Подведение итогов, обратная связь, объяснение домашнего задания, рефлексия",
      "student_activities": "Отвечают на вопросы рефлексии, записывают домашнее задание, оценивают свою работу на уроке",
      "assessment": "Рефлексия / Самооценивание",
      "resources": "Стикеры / Рефлексивные листы"
    }}
  ],
  "differentiation": {{
    "support": "Как поддержать менее успешных учеников (scaffolding, дополнительные подсказки, упрощённые задания)",
    "extension": "Как расширить знания более успешных учеников (дополнительные задания, исследовательские вопросы)",
    "assessment_of_learning": "Как учитель будет оценивать достижение целей урока"
  }},
  "reflection": {{
    "questions": [
      "Достигнуты ли цели урока? Как можно это определить?",
      "Что прошло хорошо на уроке?",
      "Какие трудности возникли? Как их преодолеть в будущем?"
    ]
  }},
  "homework": {{
    "description": "Описание домашнего задания с конкретными заданиями и страницами учебника",
    "differentiated": true,
    "tasks": [
      "Задание для всех учеников",
      "Дополнительное задание для сильных учеников (по желанию)"
    ]
  }}
}}

Требования:
- Минимум 2 цели обучения (learning_objectives) с конкретными формулировками
- Минимум 2 цели урока (lesson_objectives), измеримые и конкретные
- Минимум 2 критерия оценивания, связанных с целями урока
- Этап «Сабақтың ортасы» должен быть самым подробным (минимум 3-4 предложения для teacher_activities и student_activities)
- Конкретные задания и методы работы (не общие фразы)
- Дифференциация должна быть практичной и реализуемой
- Домашнее задание должно быть связано с темой урока"""

    system_instruction = (
        "Ты — опытный методист казахстанской школы, эксперт по составлению ҚМЖ "
        "(Қысқа мерзімді жоспар / Краткосрочный план урока). "
        "Создавай планы строго по формату казахстанского стандарта образования. "
        "Возвращай ТОЛЬКО валидный JSON без дополнительного текста."
    )

    result = await ai_service.chat(
        message=prompt,
        model=model,
        system_instruction=system_instruction,
    )

    qmj_data = _clean_ai_json(result["text"])

    # Wrap in standard content structure
    now = datetime.now(timezone.utc)

    qmj_title = qmj_data.get("lesson_info", {}).get("topic", topic)

    content = {
        "meta": {
            "title": qmj_title,
            "subject": subject,
            "grade": grade,
            "topic": topic,
            "language": language,
            "created_at": now.isoformat(),
        },
        "lesson_info": qmj_data.get("lesson_info", {}),
        "stages": qmj_data.get("stages", []),
        "differentiation": qmj_data.get("differentiation", {}),
        "reflection": qmj_data.get("reflection", {}),
        "homework": qmj_data.get("homework", {}),
    }

    # Save to TeachingMaterial table
    material = TeachingMaterial(
        user_id=user_id,
        material_type=MaterialType.QMJ,
        title=f"ҚМЖ: {qmj_title}",
        subject=subject,
        grade=grade,
        topic=topic,
        content=content,
        ai_model=model,
        estimated_time=qmj_data.get("lesson_info", {}).get("duration", 40),
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    return {"id": material.id, "content": content}
