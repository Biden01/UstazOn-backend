"""
Teaching Materials Service for generating lesson plans, tests, homework, and rubrics
"""
import logging
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.models.teaching_materials import TeachingMaterial, MaterialType, DifficultyLevel
from src.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class TeachingMaterialsService:
    """Service for generating teaching materials"""

    async def generate_lesson_plan(
        self,
        subject: str,
        grade: str,
        topic: str,
        duration: int = 45,
        model: str = "gemini-2.5-flash",
        db: AsyncSession = None,
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        Generate a structured lesson plan

        Args:
            subject: Subject name (e.g., "Математика")
            grade: Grade level (e.g., "7 класс")
            topic: Lesson topic
            duration: Lesson duration in minutes
            model: AI model to use
            db: Database session (optional, for saving)
            user_id: User ID (optional, for saving)

        Returns:
            Dictionary with lesson plan structure
        """
        prompt = f"""Создай подробный план урока по следующим параметрам:

Предмет: {subject}
Класс: {grade}
Тема: {topic}
Длительность: {duration} минут

Верни ТОЛЬКО валидный JSON в следующем формате (без markdown, без текста до или после JSON):

{{
  "title": "Название урока",
  "subject": "{subject}",
  "grade": "{grade}",
  "topic": "{topic}",
  "duration": {duration},
  "objectives": {{
    "educational": ["Образовательная цель 1", "Образовательная цель 2"],
    "developmental": ["Развивающая цель 1", "Развивающая цель 2"],
    "educational_upbringing": ["Воспитательная цель 1"]
  }},
  "materials": ["Материал 1", "Материал 2", "Материал 3"],
  "lesson_flow": [
    {{
      "stage": "Организационный момент",
      "duration": 3,
      "description": "Приветствие, проверка готовности к уроку, создание позитивной атмосферы",
      "activities": ["Приветствие", "Проверка присутствующих", "Проверка готовности"]
    }},
    {{
      "stage": "Проверка домашнего задания",
      "duration": 7,
      "description": "Проверка понимания предыдущей темы",
      "activities": ["Фронтальный опрос", "Проверка письменных заданий"]
    }},
    {{
      "stage": "Актуализация знаний",
      "duration": 5,
      "description": "Подготовка к восприятию новой темы",
      "activities": ["Повторение связанных тем", "Мотивация к изучению новой темы"]
    }},
    {{
      "stage": "Объяснение новой темы",
      "duration": 20,
      "description": "Введение и объяснение нового материала",
      "activities": ["Объяснение", "Демонстрация", "Примеры"]
    }},
    {{
      "stage": "Закрепление материала",
      "duration": 7,
      "description": "Практическое применение новых знаний",
      "activities": ["Упражнения", "Самостоятельная работа", "Групповые задания"]
    }},
    {{
      "stage": "Домашнее задание",
      "duration": 2,
      "description": "Объяснение домашнего задания",
      "activities": ["Запись домашнего задания", "Разъяснение требований"]
    }},
    {{
      "stage": "Рефлексия",
      "duration": 3,
      "description": "Подведение итогов урока",
      "activities": ["Что узнали нового?", "Что было сложно?", "Самооценка"]
    }}
  ],
  "differentiation": {{
    "basic": "Задания для учеников базового уровня",
    "medium": "Задания для учеников среднего уровня",
    "advanced": "Задания для сильных учеников"
  }},
  "assessment_criteria": ["Критерий 1", "Критерий 2", "Критерий 3"]
}}"""

        try:
            result = await ai_service.chat(
                message=prompt,
                model=model,
                system_instruction="Ты - эксперт по созданию планов уроков для казахстанских школ. Возвращай ТОЛЬКО валидный JSON без дополнительного текста."
            )

            import json
            import re

            # Extract JSON from response
            text = result["text"].strip()
            # Remove markdown code blocks if present
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)

            lesson_plan_data = json.loads(text)

            # Save to database if db and user_id provided
            if db and user_id:
                material = TeachingMaterial(
                    user_id=user_id,
                    material_type=MaterialType.LESSON_PLAN,
                    title=lesson_plan_data.get("title", topic),
                    subject=subject,
                    grade=grade,
                    topic=topic,
                    content=lesson_plan_data,
                    ai_model=model,
                    estimated_time=duration
                )
                db.add(material)
                await db.commit()
                await db.refresh(material)
                lesson_plan_data["id"] = material.id

            return lesson_plan_data

        except Exception as e:
            logger.error(f"Error generating lesson plan: {e}")
            raise

    async def generate_test(
        self,
        subject: str,
        grade: str,
        topic: str,
        question_count: int = 15,
        difficulty: str = "medium",
        question_types: list = None,
        model: str = "gemini-2.5-flash",
        db: AsyncSession = None,
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        Generate a test with various question types

        Args:
            subject: Subject name
            grade: Grade level
            topic: Test topic
            question_count: Number of questions
            difficulty: Difficulty level (easy/medium/hard/mixed)
            question_types: List of question types
            model: AI model to use
            db: Database session
            user_id: User ID

        Returns:
            Dictionary with test structure
        """
        if question_types is None:
            question_types = ["multiple_choice", "open_ended", "problem_solving"]

        types_str = ", ".join(question_types)

        prompt = f"""Создай тест/СОР по следующим параметрам:

Предмет: {subject}
Класс: {grade}
Тема: {topic}
Количество вопросов: {question_count}
Уровень сложности: {difficulty}
Типы вопросов: {types_str}

Верни ТОЛЬКО валидный JSON (без markdown):

{{
  "title": "Тест по теме: {topic}",
  "subject": "{subject}",
  "grade": "{grade}",
  "topic": "{topic}",
  "question_count": {question_count},
  "difficulty": "{difficulty}",
  "estimated_time": 30,
  "total_points": 100,
  "questions": [
    {{
      "number": 1,
      "type": "multiple_choice",
      "question": "Текст вопроса",
      "options": ["Вариант А", "Вариант Б", "Вариант В", "Вариант Г"],
      "correct_answer": "Вариант А",
      "points": 5,
      "explanation": "Объяснение правильного ответа"
    }},
    {{
      "number": 2,
      "type": "open_ended",
      "question": "Открытый вопрос",
      "correct_answer": "Примерный правильный ответ",
      "points": 10,
      "criteria": ["Критерий 1", "Критерий 2"]
    }},
    {{
      "number": 3,
      "type": "problem_solving",
      "question": "Задача",
      "solution": "Пошаговое решение",
      "correct_answer": "Ответ",
      "points": 15
    }}
  ],
  "grading_scale": {{
    "90-100": "5 (отлично)",
    "75-89": "4 (хорошо)",
    "50-74": "3 (удовлетворительно)",
    "0-49": "2 (неудовлетворительно)"
  }}
}}"""

        try:
            result = await ai_service.chat(
                message=prompt,
                model=model,
                system_instruction="Ты - эксперт по созданию тестов для казахстанских школ. Возвращай ТОЛЬКО валидный JSON."
            )

            import json
            import re

            text = result["text"].strip()
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)

            test_data = json.loads(text)

            # Save to database
            if db and user_id:
                material = TeachingMaterial(
                    user_id=user_id,
                    material_type=MaterialType.TEST,
                    title=test_data.get("title", f"Тест: {topic}"),
                    subject=subject,
                    grade=grade,
                    topic=topic,
                    content=test_data,
                    ai_model=model,
                    difficulty_level=DifficultyLevel(difficulty) if difficulty in ["easy", "medium", "hard", "mixed"] else DifficultyLevel.MEDIUM,
                    question_count=question_count,
                    estimated_time=test_data.get("estimated_time", 30)
                )
                db.add(material)
                await db.commit()
                await db.refresh(material)
                test_data["id"] = material.id

            return test_data

        except Exception as e:
            logger.error(f"Error generating test: {e}")
            raise

    async def generate_homework(
        self,
        subject: str,
        grade: str,
        topic: str,
        duration: int = 30,
        difficulty: str = "medium",
        model: str = "gemini-2.5-flash",
        db: AsyncSession = None,
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        Generate homework assignment

        Args:
            subject: Subject name
            grade: Grade level
            topic: Homework topic
            duration: Expected completion time in minutes
            difficulty: Difficulty level
            model: AI model to use
            db: Database session
            user_id: User ID

        Returns:
            Dictionary with homework structure
        """
        prompt = f"""Создай домашнее задание по следующим параметрам:

Предмет: {subject}
Класс: {grade}
Тема: {topic}
Время на выполнение: {duration} минут
Уровень сложности: {difficulty}

Верни ТОЛЬКО валидный JSON (без markdown):

{{
  "title": "Домашнее задание по теме: {topic}",
  "subject": "{subject}",
  "grade": "{grade}",
  "topic": "{topic}",
  "duration": {duration},
  "difficulty": "{difficulty}",
  "instructions": "Общие инструкции для выполнения домашнего задания",
  "tasks": [
    {{
      "number": 1,
      "type": "theory",
      "task": "Теоретическое задание (повторение, чтение)",
      "description": "Подробное описание задания",
      "points": 5
    }},
    {{
      "number": 2,
      "type": "practice",
      "task": "Практическое задание (упражнения, задачи)",
      "description": "Подробное описание с примерами",
      "points": 10
    }},
    {{
      "number": 3,
      "type": "creative",
      "task": "Творческое задание",
      "description": "Описание творческого элемента",
      "points": 5
    }}
  ],
  "assessment_criteria": [
    "Полнота выполнения заданий",
    "Правильность ответов",
    "Аккуратность оформления",
    "Творческий подход"
  ],
  "tips": [
    "Совет 1 для учеников",
    "Совет 2 для учеников"
  ]
}}"""

        try:
            result = await ai_service.chat(
                message=prompt,
                model=model,
                system_instruction="Ты - эксперт по созданию домашних заданий для казахстанских школ. Возвращай ТОЛЬКО валидный JSON."
            )

            import json
            import re

            text = result["text"].strip()
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)

            homework_data = json.loads(text)

            # Save to database
            if db and user_id:
                material = TeachingMaterial(
                    user_id=user_id,
                    material_type=MaterialType.HOMEWORK,
                    title=homework_data.get("title", f"Д/З: {topic}"),
                    subject=subject,
                    grade=grade,
                    topic=topic,
                    content=homework_data,
                    ai_model=model,
                    difficulty_level=DifficultyLevel(difficulty) if difficulty in ["easy", "medium", "hard", "mixed"] else DifficultyLevel.MEDIUM,
                    estimated_time=duration
                )
                db.add(material)
                await db.commit()
                await db.refresh(material)
                homework_data["id"] = material.id

            return homework_data

        except Exception as e:
            logger.error(f"Error generating homework: {e}")
            raise

    async def generate_rubric(
        self,
        subject: str,
        grade: str,
        work_type: str,
        description: str,
        model: str = "gemini-2.5-flash",
        db: AsyncSession = None,
        user_id: int = None
    ) -> Dict[str, Any]:
        """
        Generate assessment rubric

        Args:
            subject: Subject name
            grade: Grade level
            work_type: Type of work (test/project/presentation/essay)
            description: Description of the work
            model: AI model to use
            db: Database session
            user_id: User ID

        Returns:
            Dictionary with rubric structure
        """
        prompt = f"""Создай критерии оценивания (рубрику) по следующим параметрам:

Предмет: {subject}
Класс: {grade}
Тип работы: {work_type}
Описание работы: {description}

Верни ТОЛЬКО валидный JSON (без markdown):

{{
  "title": "Критерии оценивания: {work_type}",
  "subject": "{subject}",
  "grade": "{grade}",
  "work_type": "{work_type}",
  "description": "{description}",
  "criteria": [
    {{
      "name": "Название критерия 1",
      "description": "Описание критерия",
      "max_points": 25,
      "levels": {{
        "excellent": {{
          "points": "23-25",
          "description": "Описание отличного выполнения"
        }},
        "good": {{
          "points": "18-22",
          "description": "Описание хорошего выполнения"
        }},
        "satisfactory": {{
          "points": "13-17",
          "description": "Описание удовлетворительного выполнения"
        }},
        "unsatisfactory": {{
          "points": "0-12",
          "description": "Описание неудовлетворительного выполнения"
        }}
      }}
    }},
    {{
      "name": "Название критерия 2",
      "description": "Описание критерия",
      "max_points": 25,
      "levels": {{
        "excellent": {{"points": "23-25", "description": "..."}},
        "good": {{"points": "18-22", "description": "..."}},
        "satisfactory": {{"points": "13-17", "description": "..."}},
        "unsatisfactory": {{"points": "0-12", "description": "..."}}
      }}
    }}
  ],
  "total_points": 100,
  "grading_scale": {{
    "90-100": "5 (отлично)",
    "75-89": "4 (хорошо)",
    "50-74": "3 (удовлетворительно)",
    "0-49": "2 (неудовлетворительно)"
  }}
}}"""

        try:
            result = await ai_service.chat(
                message=prompt,
                model=model,
                system_instruction="Ты - эксперт по созданию критериев оценивания для казахстанских школ. Возвращай ТОЛЬКО валидный JSON."
            )

            import json
            import re

            text = result["text"].strip()
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)

            rubric_data = json.loads(text)

            # Save to database
            if db and user_id:
                material = TeachingMaterial(
                    user_id=user_id,
                    material_type=MaterialType.RUBRIC,
                    title=rubric_data.get("title", f"Рубрика: {work_type}"),
                    subject=subject,
                    grade=grade,
                    topic=description[:300],  # Use description as topic, truncate if too long
                    content=rubric_data,
                    ai_model=model
                )
                db.add(material)
                await db.commit()
                await db.refresh(material)
                rubric_data["id"] = material.id

            return rubric_data

        except Exception as e:
            logger.error(f"Error generating rubric: {e}")
            raise

    @staticmethod
    def export_to_docx(material_data: Dict[str, Any], material_type: MaterialType) -> BytesIO:
        """
        Export teaching material to DOCX format

        Args:
            material_data: Material data dictionary
            material_type: Type of material

        Returns:
            BytesIO object containing DOCX file
        """
        try:
            doc = Document()

            # Set styles
            style = doc.styles['Normal']
            font = style.font
            font.name = 'Arial'
            font.size = Pt(11)

            # Title
            title = doc.add_heading(material_data.get("title", "Учебный материал"), level=1)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Metadata
            doc.add_paragraph(f"Предмет: {material_data.get('subject', 'Не указан')}")
            doc.add_paragraph(f"Класс: {material_data.get('grade', 'Не указан')}")
            doc.add_paragraph(f"Тема: {material_data.get('topic', 'Не указана')}")
            doc.add_paragraph("")

            # Type-specific content
            if material_type == MaterialType.LESSON_PLAN:
                TeachingMaterialsService._add_lesson_plan_content(doc, material_data)
            elif material_type == MaterialType.TEST:
                TeachingMaterialsService._add_test_content(doc, material_data)
            elif material_type == MaterialType.HOMEWORK:
                TeachingMaterialsService._add_homework_content(doc, material_data)
            elif material_type == MaterialType.RUBRIC:
                TeachingMaterialsService._add_rubric_content(doc, material_data)

            # Save to BytesIO
            docx_output = BytesIO()
            doc.save(docx_output)
            docx_output.seek(0)

            return docx_output

        except Exception as e:
            logger.error(f"Error exporting to DOCX: {e}")
            raise

    @staticmethod
    def _add_lesson_plan_content(doc: Document, data: Dict[str, Any]):
        """Add lesson plan content to document"""
        # Objectives
        doc.add_heading("Цели урока", level=2)
        objectives = data.get("objectives", {})
        if objectives.get("educational"):
            doc.add_paragraph("Образовательные:", style='List Bullet')
            for obj in objectives["educational"]:
                doc.add_paragraph(obj, style='List Bullet 2')
        if objectives.get("developmental"):
            doc.add_paragraph("Развивающие:", style='List Bullet')
            for obj in objectives["developmental"]:
                doc.add_paragraph(obj, style='List Bullet 2')
        if objectives.get("educational_upbringing"):
            doc.add_paragraph("Воспитательные:", style='List Bullet')
            for obj in objectives["educational_upbringing"]:
                doc.add_paragraph(obj, style='List Bullet 2')

        # Materials
        doc.add_heading("Материалы и оборудование", level=2)
        for material in data.get("materials", []):
            doc.add_paragraph(material, style='List Bullet')

        # Lesson flow
        doc.add_heading("Ход урока", level=2)
        for stage in data.get("lesson_flow", []):
            doc.add_heading(f"{stage.get('stage')} ({stage.get('duration')} мин)", level=3)
            doc.add_paragraph(stage.get("description", ""))
            for activity in stage.get("activities", []):
                doc.add_paragraph(activity, style='List Bullet')

        # Differentiation
        doc.add_heading("Дифференциация", level=2)
        diff = data.get("differentiation", {})
        if diff.get("basic"):
            doc.add_paragraph(f"Базовый уровень: {diff['basic']}")
        if diff.get("medium"):
            doc.add_paragraph(f"Средний уровень: {diff['medium']}")
        if diff.get("advanced"):
            doc.add_paragraph(f"Высокий уровень: {diff['advanced']}")

        # Assessment criteria
        doc.add_heading("Критерии оценивания", level=2)
        for criterion in data.get("assessment_criteria", []):
            doc.add_paragraph(criterion, style='List Bullet')

    @staticmethod
    def _add_test_content(doc: Document, data: Dict[str, Any]):
        """Add test content to document"""
        doc.add_paragraph(f"Всего вопросов: {data.get('question_count', 'Не указано')}")
        doc.add_paragraph(f"Время: {data.get('estimated_time', 'Не указано')} минут")
        doc.add_paragraph(f"Максимальный балл: {data.get('total_points', 100)}")
        doc.add_paragraph("")

        doc.add_heading("Вопросы", level=2)
        for question in data.get("questions", []):
            doc.add_heading(f"Вопрос {question.get('number')} ({question.get('points')} баллов)", level=3)
            doc.add_paragraph(question.get("question", ""))

            if question.get("type") == "multiple_choice" and question.get("options"):
                for option in question["options"]:
                    doc.add_paragraph(option, style='List Bullet')

            doc.add_paragraph(f"Правильный ответ: {question.get('correct_answer', 'Не указан')}")
            if question.get("explanation"):
                doc.add_paragraph(f"Объяснение: {question['explanation']}")
            doc.add_paragraph("")

    @staticmethod
    def _add_homework_content(doc: Document, data: Dict[str, Any]):
        """Add homework content to document"""
        doc.add_paragraph(f"Время на выполнение: {data.get('duration', 'Не указано')} минут")
        doc.add_paragraph(f"Уровень сложности: {data.get('difficulty', 'Средний')}")
        doc.add_paragraph("")

        if data.get("instructions"):
            doc.add_heading("Инструкции", level=2)
            doc.add_paragraph(data["instructions"])

        doc.add_heading("Задания", level=2)
        for task in data.get("tasks", []):
            doc.add_heading(f"Задание {task.get('number')} ({task.get('type')}) - {task.get('points')} баллов", level=3)
            doc.add_paragraph(f"Задание: {task.get('task', '')}")
            doc.add_paragraph(f"Описание: {task.get('description', '')}")
            doc.add_paragraph("")

        if data.get("tips"):
            doc.add_heading("Советы", level=2)
            for tip in data["tips"]:
                doc.add_paragraph(tip, style='List Bullet')

    @staticmethod
    def _add_rubric_content(doc: Document, data: Dict[str, Any]):
        """Add rubric content to document"""
        doc.add_paragraph(f"Тип работы: {data.get('work_type', 'Не указан')}")
        doc.add_paragraph(f"Максимальный балл: {data.get('total_points', 100)}")
        doc.add_paragraph("")

        doc.add_heading("Критерии оценивания", level=2)
        for criterion in data.get("criteria", []):
            doc.add_heading(f"{criterion.get('name')} (макс. {criterion.get('max_points')} баллов)", level=3)
            doc.add_paragraph(criterion.get("description", ""))

            levels = criterion.get("levels", {})
            for level_name, level_data in levels.items():
                level_title = {"excellent": "Отлично", "good": "Хорошо", "satisfactory": "Удовлетворительно", "unsatisfactory": "Неудовлетворительно"}
                doc.add_paragraph(f"{level_title.get(level_name, level_name)}: {level_data.get('points')} баллов", style='List Bullet')
                doc.add_paragraph(level_data.get("description", ""), style='List Bullet 2')


# Create singleton instance
teaching_materials_service = TeachingMaterialsService()
