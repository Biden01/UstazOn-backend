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
    "section": "Название раздела/бөлім из учебной программы, к которому относится тема",
    "duration": 40,
    "learning_objectives": [
      "Код.из.программы — формулировка цели обучения (например: 8.4.1.2 квадраттық функциялардың қасиеттерін білу және графиктерін салу)"
    ],
    "lesson_objectives": [
      "Конкретная, измеримая цель урока — что именно ученики смогут делать к концу урока"
    ],
    "assessment_criteria": [
      "Критерий оценивания, связанный с целями урока"
    ],
    "values_education": {{
      "value_name": "Название конкретной ценности (например: Заң және Тәртіп, Жасампаздық және Жаңашылдық, Еңбек және шығармашылық, Ұлттық бірлік, Адамгершілік, Патриотизм и т.д.)",
      "value_description": "Подробное описание: как именно эта ценность раскрывается на данном уроке. 2-3 предложения о том, как через содержание урока привить эту ценность.",
      "value_sentences": [
        "Незавершённое предложение для обсуждения с учениками 1 ...",
        "Незавершённое предложение 2 ...",
        "Незавершённое предложение 3 ...",
        "Незавершённое предложение 4 ...",
        "Незавершённое предложение 5 ..."
      ]
    }},
    "cross_curricular_links": "Пәнаралық байланыс / Межпредметные связи",
    "prior_knowledge": "Алдыңғы білім / Предшествующие знания — что ученики уже должны знать",
    "resources": [
      "Оқулық (название учебника и автора)",
      "Слайд / Презентация",
      "Тақта, бор",
      "Дәптер",
      "Wordwall / интерактивная платформа"
    ]
  }},
  "stages": [
    {{
      "name": "Ұйымдастыру кезеңі",
      "name_ru": "Организационный этап",
      "duration": 5,
      "work_type": "Тип работы (топтық/жұптық/жеке)",
      "method": "Название метода (например: «Сөйлемді жалғастыр», «Миға шабуыл»)",
      "teacher_activities": "Подробное описание: создание психологической атмосферы, знакомство с целями урока, мотивация через ценности",
      "student_activities": "Что делают ученики: слушают, продолжают предложения по ценностям, настраиваются на урок",
      "assessment": "Метод оценивания (например: «Шапалақ» әдісі, ауызша бағалау)",
      "resources": "Ресурсы данного этапа"
    }},
    {{
      "name": "Сабақтың басы",
      "name_ru": "Начало урока",
      "duration": 10,
      "work_type": "Тип работы",
      "method": "Метод",
      "teacher_activities": "Объяснение нового материала с формулами, определениями и примерами. Подробное описание теории по теме урока.",
      "student_activities": "Слушают, записывают, задают вопросы по непонятным моментам",
      "assessment": "Мақтау-мадақтау арқылы бағалау (Жарайсың! Өте жақсы! Керемет!)",
      "resources": "Тақта, слайд, оқулық"
    }},
    {{
      "name": "Сабақтың ортасы",
      "name_ru": "Середина урока",
      "duration": 25,
      "exercises": [
        {{
          "number": "Номер задания из учебника (например: №3.4 или №857)",
          "text": "Полный текст задания как в учебнике",
          "work_type": "Тип работы (жеке/жұптық/топтық)",
          "descriptors": [
            "Оқушы: конкретный дескриптор 1 — что именно должен сделать ученик",
            "конкретный дескриптор 2",
            "конкретный дескриптор 3"
          ],
          "assessment_method": "Метод оценивания (ҚБ: жұптық тексеру / «Бағдаршам» / өзін-өзі бағалау / Think-Pair-Share / «Екі жұлдыз, бір тілек» / мини-тақта)",
          "resources": "Ресурсы для данного задания"
        }},
        {{
          "number": "Следующее задание",
          "text": "Текст задания",
          "work_type": "Тип работы",
          "descriptors": [
            "дескриптор 1",
            "дескриптор 2"
          ],
          "assessment_method": "Метод оценивания",
          "resources": "Ресурсы"
        }}
      ]
    }},
    {{
      "name": "Сабақтың соңы",
      "name_ru": "Конец урока",
      "duration": 5,
      "teacher_activities": "Кері байланыс алу, үй тапсырмасын беру, бағаларды жария ету",
      "student_activities": "Кері байланыс: Түсіндім / Сұрақтарым бар / Түсінбедім. Үй тапсырмасын жазып алу.",
      "assessment": "Бағалау парақтары бойынша 1-10 баллмен бағалау",
      "resources": "Бағалау парағы"
    }}
  ],
  "differentiation": {{
    "support": "Как поддержать менее успешных учеников (scaffolding, дополнительные подсказки, упрощённые задания)",
    "extension": "Как расширить знания более успешных учеников (дополнительные задания, исследовательские вопросы)",
    "assessment_of_learning": "Как учитель будет оценивать достижение целей урока"
  }},
  "reflection": {{
    "questions": [
      "Сабақ мақсаттарына қол жеткізілді ме?",
      "Сабақта не жақсы өтті?",
      "Қандай қиындықтар туындады? Оларды болашақта қалай жеңуге болады?"
    ]
  }},
  "homework": {{
    "description": "Описание домашнего задания",
    "exercise_number": "Конкретный номер задания из учебника (например: №13.12)",
    "tasks": [
      "Основное задание для всех учеников",
      "Дополнительное задание для сильных учеников (по желанию)"
    ]
  }}
}}

Требования:
- Минимум 2 цели обучения (learning_objectives) с КОДАМИ из учебной программы Казахстана (формат: X.X.X.X)
- Минимум 2 цели урока (lesson_objectives), измеримые и конкретные
- Минимум 2 критерия оценивания, связанных с целями урока
- Раздел (section) ОБЯЗАТЕЛЬНО — название раздела из учебной программы
- Құндылыққа баулу (values_education) ОБЯЗАТЕЛЬНО с конкретной ценностью и 5 незавершёнными предложениями для обсуждения
- Этап «Сабақтың ортасы» должен содержать минимум 3 упражнения (exercises) с полным текстом задания и дескрипторами
- Каждое упражнение должно иметь 3-6 дескрипторов, описывающих конкретные действия ученика
- Методы оценивания должны быть разнообразными: «Бағдаршам», Think-Pair-Share, «Екі жұлдыз, бір тілек», жұптық тексеру, мини-тақта и т.д.
- Номера заданий должны быть реалистичными для данного учебника
- Ресурсы должны быть конкретными: оқулық, дәптер, слайд, тақта, Wordwall и т.д.
- Домашнее задание должно содержать конкретный номер из учебника"""

    system_instruction = (
        "Ты — опытный методист казахстанской школы, эксперт по составлению ҚМЖ "
        "(Қысқа мерзімді жоспар / Краткосрочный план урока). "
        "Создавай планы строго по формату казахстанского стандарта образования. "
        "Ты знаешь программу Казахстана для всех предметов 1-11 классов. "
        "Используй реальные коды из учебной программы (формат X.X.X.X). "
        "Каждое упражнение должно иметь подробные дескрипторы. "
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

    lesson_info = qmj_data.get("lesson_info", {})

    # Backward compatibility: convert old "values" string to new values_education format
    if "values_education" not in lesson_info and "values" in lesson_info:
        lesson_info["values_education"] = {
            "value_name": lesson_info.pop("values", ""),
            "value_description": "",
            "value_sentences": [],
        }

    content = {
        "meta": {
            "title": qmj_title,
            "subject": subject,
            "grade": grade,
            "topic": topic,
            "language": language,
            "created_at": now.isoformat(),
        },
        "lesson_info": lesson_info,
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
