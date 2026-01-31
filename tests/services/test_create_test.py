import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.db.base import Base
from src.models.user import User
from src.models.test import Test, Question, Answer
from src.schemas.test import TestCreate, QuestionCreate, AnswerCreate
from src.services.test_service import create_test


@pytest_asyncio.fixture
async def async_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Create a user row so the FK constraint is satisfied
        user = User(
            id=1,
            iin="123456789012",
            name="Test User",
            phone="+77001234567",
            hashed_password="fakehash",
        )
        session.add(user)
        await session.commit()

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _build_test_create() -> TestCreate:
    questions = []
    for q_idx in range(2):
        answers = [
            AnswerCreate(text=f"Answer {label} for Q{q_idx + 1}", is_correct=(label == "A"))
            for label in ("A", "B", "C", "D")
        ]
        questions.append(QuestionCreate(text=f"Question {q_idx + 1}", answers=answers))

    return TestCreate(
        title="Unit Test Exam",
        subject="Mathematics",
        difficulty="medium",
        questions=questions,
    )


TEST_USER_ID = 1


@pytest.mark.asyncio
async def test_create_test(async_db_session: AsyncSession):
    db = async_db_session
    test_data = _build_test_create()

    result = await create_test(db, test_data, TEST_USER_ID)

    # --- Test record ---
    assert result.id is not None
    assert result.user_id == TEST_USER_ID

    # --- Verify via SELECT (data persisted) ---
    row = await db.execute(
        select(Test)
        .where(Test.id == result.id)
        .options(
            selectinload(Test.questions).selectinload(Question.answers),
        )
    )
    test_obj = row.scalar_one()
    assert test_obj is not None
    assert test_obj.user_id == TEST_USER_ID

    # --- Questions ---
    questions = sorted(test_obj.questions, key=lambda q: q.order)
    assert len(questions) == 2

    for idx, question in enumerate(questions):
        expected_order = idx + 1  # create_test uses enumerate(..., start=1)
        assert question.order == expected_order, f"Question {idx} order mismatch"
        assert question.text == f"Question {idx + 1}"

        # --- Answers ---
        answers = sorted(question.answers, key=lambda a: a.order)
        assert len(answers) == 4, f"Question {idx} should have 4 answers"

        correct_count = sum(1 for a in answers if a.is_correct)
        assert correct_count == 1, f"Question {idx} must have exactly 1 correct answer"

        for a_idx, answer in enumerate(answers):
            expected_a_order = a_idx + 1  # create_test uses enumerate(..., start=1)
            assert answer.order == expected_a_order, f"Q{idx} Answer {a_idx} order mismatch"

        # First answer (A) should be the correct one
        assert answers[0].is_correct is True
        for a in answers[1:]:
            assert a.is_correct is False
