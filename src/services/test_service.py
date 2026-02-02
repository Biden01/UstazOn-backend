from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from io import BytesIO
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import logging

from src.models.test import Test, Question, Answer
from src.schemas.test import (
    TestCreate,
    TestUpdate,
    QuestionCreate,
    QuestionUpdate,
    AnswerCreate,
    AnswerUpdate,
    TestSubmission,
    TestResult,
)
from src.schemas.ai_schemas import TestData
from src.models.test import DifficultyLevel
from src.utils.llm_repair import normalize_test_data

logger = logging.getLogger(__name__)


def _validate_test_data_with_repair(raw_data: dict) -> TestData:
    """
    Validate LLM output against TestData schema with a single repair retry.

    1. Try strict validation.
    2. On ValidationError → normalize known typos → retry once.
    3. If still invalid → raise the *original* ValidationError.
    """
    from pydantic import ValidationError

    try:
        return TestData.model_validate(raw_data)
    except ValidationError as first_err:
        logger.warning(
            "TestData validation failed on raw LLM output, attempting repair. "
            "Raw data: %s | Error: %s",
            raw_data,
            first_err,
        )

    normalized = normalize_test_data(raw_data)
    logger.info("Normalized LLM output: %s", normalized)

    try:
        return TestData.model_validate(normalized)
    except ValidationError:
        logger.error(
            "TestData validation failed after repair. "
            "Normalized data: %s | Original error: %s",
            normalized,
            first_err,
        )
        raise first_err


async def generate_and_save_test(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: str,
    topic: str,
    question_count: int,
    difficulty: str,
    model: str = "claude-3-5-sonnet-latest",
) -> Test:
    """
    Generate a test using AI and save it to the database.

    1. Calls AI to generate structured test JSON
    2. Validates via TestData schema
    3. Transforms to TestCreate format
    4. Persists using create_test()
    """
    from src.services.ai_service import ai_service
    from src.prompts.teacher_prompts import QUICK_PROMPTS

    test_prompt = QUICK_PROMPTS["test"]["prompt"]

    user_message = f"""Пән: {subject}
Сынып: {grade}
Тақырып: {topic}
Сұрақтар саны: {question_count}
Күрделілік деңгейі: {difficulty}

{test_prompt}"""

    raw_data = await ai_service.generate_with_retry(
        prompt=user_message,
        max_retries=2,
        system_instruction=(
            "Сен — білім беру тесттерін жасау бойынша сарапшысың. "
            "Барлық мазмұнды ТІЛІ ҚАЗАҚША жаз. "
            "ТІЛЬКИ жарамды JSON қайтар, қосымша мәтінсіз.\n"
            "Әрбір option ТІЛЬКИ \"label\" және \"text\" кілттерін қамтуы КЕРЕК. "
            "\"text_answer\" ЕШҚАШАН қолданба — \"text\" қолдан.\n"
            "Әрбір сұрақта дәл 4 жауап нұсқасы болуы керек."
        ),
        model=model,
    )

    validated = _validate_test_data_with_repair(raw_data)

    questions = []
    for q in validated.questions:
        answers = []
        for opt in q.options:
            answers.append(
                AnswerCreate(
                    text=opt.text,
                    is_correct=(opt.label == q.correct_answer),
                )
            )
        questions.append(QuestionCreate(text=q.question_text, answers=answers))

    test_create = TestCreate(
        title=validated.title,
        subject=subject,
        difficulty=DifficultyLevel(difficulty),
        questions=questions,
    )

    test = await create_test(db, test_create, user_id)
    return test


# Test CRUD
async def get_tests(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    user_id: int | None = None,
    subject: str | None = None,
    difficulty: str | None = None,
) -> list[Test]:
    """Get tests with optional filters"""
    query = select(Test).options(selectinload(Test.questions))

    # Apply filters
    filters = []
    if user_id is not None:
        filters.append(Test.user_id == user_id)
    if subject is not None:
        filters.append(Test.subject == subject)
    if difficulty is not None:
        filters.append(Test.difficulty == difficulty)

    if filters:
        query = query.where(and_(*filters))

    query = query.offset(skip).limit(limit).order_by(Test.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_test_by_id(db: AsyncSession, test_id: int) -> Test | None:
    """Get test by ID with all questions and answers"""
    result = await db.execute(
        select(Test)
        .where(Test.id == test_id)
        .options(
            selectinload(Test.questions).selectinload(Question.answers),
            selectinload(Test.user),
        )
    )
    return result.scalar_one_or_none()


async def create_test(db: AsyncSession, test_data: TestCreate, user_id: int) -> Test:
    """Create new test with questions and answers"""
    # Extract questions data
    questions_data = test_data.questions

    # Create test without questions
    test_dict = test_data.model_dump(exclude={"questions"})
    test = Test(**test_dict, user_id=user_id)
    db.add(test)
    await db.flush()  # Get test ID

    # Create questions with answers
    for q_idx, q_data in enumerate(questions_data):
        answers_data = q_data.answers
        question_dict = q_data.model_dump(exclude={"answers", "order"})
        question = Question(**question_dict, test_id=test.id, order=q_idx)
        db.add(question)
        await db.flush()  # Get question ID

        # Create answers
        for a_idx, a_data in enumerate(answers_data):
            answer = Answer(
                **a_data.model_dump(exclude={"order"}), question_id=question.id, order=a_idx
            )
            db.add(answer)

    await db.commit()
    await db.refresh(test)
    return test


async def update_test(
    db: AsyncSession, test_id: int, test_data: TestUpdate
) -> Test | None:
    """Update test basic info (not questions)"""
    test = await get_test_by_id(db, test_id)
    if not test:
        return None

    update_data = test_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test, field, value)

    await db.commit()
    await db.refresh(test)
    return test


async def delete_test(db: AsyncSession, test_id: int) -> bool:
    """Delete test (cascade deletes questions and answers)"""
    test = await get_test_by_id(db, test_id)
    if not test:
        return False

    await db.delete(test)
    await db.commit()
    return True


# Question CRUD
async def add_question_to_test(
    db: AsyncSession, test_id: int, question_data: QuestionCreate
) -> Question | None:
    """Add a new question to existing test"""
    test = await get_test_by_id(db, test_id)
    if not test:
        return None

    # Extract answers data
    answers_data = question_data.answers

    # Create question
    question_dict = question_data.model_dump(exclude={"answers"})
    question = Question(**question_dict, test_id=test_id)
    db.add(question)
    await db.flush()

    # Create answers
    for a_idx, a_data in enumerate(answers_data):
        answer = Answer(**a_data.model_dump(), question_id=question.id, order=a_idx)
        db.add(answer)

    await db.commit()
    await db.refresh(question)
    return question


async def update_question(
    db: AsyncSession, question_id: int, question_data: QuestionUpdate
) -> Question | None:
    """Update question"""
    result = await db.execute(
        select(Question)
        .where(Question.id == question_id)
        .options(selectinload(Question.answers))
    )
    question = result.scalar_one_or_none()
    if not question:
        return None

    update_data = question_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    await db.commit()
    await db.refresh(question)
    return question


async def delete_question(db: AsyncSession, question_id: int) -> bool:
    """Delete question (cascade deletes answers)"""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        return False

    await db.delete(question)
    await db.commit()
    return True


# Answer CRUD
async def add_answer_to_question(
    db: AsyncSession, question_id: int, answer_data: AnswerCreate
) -> Answer | None:
    """Add a new answer to existing question"""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        return None

    answer = Answer(**answer_data.model_dump(), question_id=question_id)
    db.add(answer)
    await db.commit()
    await db.refresh(answer)
    return answer


async def update_answer(
    db: AsyncSession, answer_id: int, answer_data: AnswerUpdate
) -> Answer | None:
    """Update answer"""
    result = await db.execute(select(Answer).where(Answer.id == answer_id))
    answer = result.scalar_one_or_none()
    if not answer:
        return None

    update_data = answer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(answer, field, value)

    await db.commit()
    await db.refresh(answer)
    return answer


async def delete_answer(db: AsyncSession, answer_id: int) -> bool:
    """Delete answer"""
    result = await db.execute(select(Answer).where(Answer.id == answer_id))
    answer = result.scalar_one_or_none()
    if not answer:
        return False

    await db.delete(answer)
    await db.commit()
    return True


# Test taking and grading
async def grade_test_submission(
    db: AsyncSession, submission: TestSubmission
) -> TestResult | None:
    """Grade a test submission and return results"""
    test = await get_test_by_id(db, submission.test_id)
    if not test:
        return None

    total_questions = len(test.questions)
    correct_answers = 0

    # Create a map of user's answers
    user_answers = {ans.question_id: ans.answer_id for ans in submission.answers}

    # Check each question
    for question in test.questions:
        user_answer_id = user_answers.get(question.id)
        if user_answer_id:
            # Find the answer
            for answer in question.answers:
                if answer.id == user_answer_id and answer.is_correct:
                    correct_answers += 1
                    break

    # Calculate score
    score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    passed = score_percentage >= 70.0

    return TestResult(
        test_id=submission.test_id,
        total_questions=total_questions,
        correct_answers=correct_answers,
        score_percentage=round(score_percentage, 2),
        passed=passed,
    )


# Test document generation
def create_test_document(test_data: dict, include_answers: bool = False) -> BytesIO:
    """
    Create a DOCX test document from structured data

    Args:
        test_data: Dictionary with test structure:
            {
                "title": "Test Title",
                "instructions": "Instructions for students",
                "questions": [
                    {
                        "question_number": 1,
                        "question_text": "Question text",
                        "options": [
                            {"label": "A", "text": "Option A"},
                            {"label": "B", "text": "Option B"},
                            {"label": "C", "text": "Option C"},
                            {"label": "D", "text": "Option D"}
                        ],
                        "correct_answer": "A"
                    }
                ]
            }
        include_answers: Whether to include answer key at the end

    Returns:
        BytesIO object containing the DOCX file
    """
    try:
        # Validate the test data using Pydantic model (with LLM typo repair)
        validated_data = _validate_test_data_with_repair(test_data)

        doc = Document()

        # Set margins (2cm all sides)
        sections = doc.sections
        for section in sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2)
            section.right_margin = Cm(2)

        # Add title (centered, bold, 18pt)
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title.add_run(validated_data.title)
        title_run.bold = True
        title_run.font.size = Pt(18)
        title_run.font.name = "Times New Roman"

        # Add spacing after title
        title.paragraph_format.space_after = Pt(12)

        # Add instructions if present
        if validated_data.instructions:
            instr_para = doc.add_paragraph()
            instr_run = instr_para.add_run(validated_data.instructions)
            instr_run.font.size = Pt(12)
            instr_run.font.name = "Times New Roman"
            instr_run.italic = True
            instr_para.paragraph_format.space_after = Pt(12)
            instr_para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            instr_para.paragraph_format.line_spacing = 1.15

        # Add questions
        for question in validated_data.questions:
            # Question number and text (bold, 12pt)
            q_para = doc.add_paragraph()
            q_run = q_para.add_run(f"{question.question_number}. {question.question_text}")
            q_run.bold = True
            q_run.font.size = Pt(12)
            q_run.font.name = "Times New Roman"
            q_para.paragraph_format.space_after = Pt(6)
            q_para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            q_para.paragraph_format.line_spacing = 1.15

            # Add options
            for option in question.options:
                opt_para = doc.add_paragraph()
                opt_para.paragraph_format.left_indent = Cm(1)
                # Radio button placeholder: ○
                opt_run = opt_para.add_run(f"○  {option.label}) {option.text}")
                opt_run.font.size = Pt(12)
                opt_run.font.name = "Times New Roman"
                opt_para.paragraph_format.space_after = Pt(3)
                opt_para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
                opt_para.paragraph_format.line_spacing = 1.15

            # Add spacing between questions
            spacing_para = doc.add_paragraph()
            spacing_para.paragraph_format.space_after = Pt(12)

        # Add answer key section if requested
        if include_answers:
            # Add page break or extra spacing
            doc.add_paragraph()
            doc.add_paragraph()

            # Answer key title
            answer_title = doc.add_paragraph()
            answer_title_run = answer_title.add_run("Ответы:")
            answer_title_run.bold = True
            answer_title_run.font.size = Pt(14)
            answer_title_run.font.name = "Times New Roman"
            answer_title.paragraph_format.space_after = Pt(12)

            # List answers
            for question in validated_data.questions:
                answer_para = doc.add_paragraph()
                answer_run = answer_para.add_run(f"{question.question_number}. {question.correct_answer}")
                answer_run.font.size = Pt(12)
                answer_run.font.name = "Times New Roman"
                answer_para.paragraph_format.space_after = Pt(3)

        # Save to BytesIO
        docx_output = BytesIO()
        doc.save(docx_output)
        docx_output.seek(0)

        return docx_output

    except Exception as e:
        logger.error(f"Error creating test document: {e}")
        raise
