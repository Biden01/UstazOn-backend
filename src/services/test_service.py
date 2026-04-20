from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        question_dict = q_data.model_dump(exclude={"answers"})
        question = Question(**question_dict, test_id=test.id, order=q_idx)
        db.add(question)
        await db.flush()  # Get question ID

        # Create answers
        for a_idx, a_data in enumerate(answers_data):
            answer = Answer(
                **a_data.model_dump(), question_id=question.id, order=a_idx
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
