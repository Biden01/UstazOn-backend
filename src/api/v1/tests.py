from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.schemas.test import (
    TestCreate,
    TestUpdate,
    TestResponse,
    TestDetailResponse,
    TestPublicResponse,
    TestTakeResponse,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    AnswerCreate,
    AnswerUpdate,
    AnswerResponse,
    TestSubmission,
    TestResult,
)
from src.services import test_service

router = APIRouter()


# Test endpoints
@router.get("/", response_model=list[TestResponse])
async def get_tests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    subject: str | None = None,
    difficulty: str | None = None,
    author_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all tests with optional filters"""
    return await test_service.get_tests(
        db, skip=skip, limit=limit, user_id=author_id, subject=subject, difficulty=difficulty
    )


@router.get("/my", response_model=list[TestResponse])
async def get_my_tests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get tests created by current user"""
    return await test_service.get_tests(db, skip=skip, limit=limit, user_id=current_user.id)


@router.post("/", response_model=TestDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_test(
    test_data: TestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new test with questions and answers"""
    return await test_service.create_test(db, test_data, current_user.id)


@router.get("/{test_id}", response_model=TestDetailResponse)
async def get_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get test by ID with all questions and answers (for authors only)"""
    test = await test_service.get_test_by_id(db, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )

    # Only author can see full test with correct answers
    if test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only test author can view full test details",
        )

    return test


@router.get("/{test_id}/public", response_model=TestPublicResponse)
async def get_test_public(
    test_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get test basic info (public)"""
    test = await test_service.get_test_by_id(db, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )
    return test


@router.get("/{test_id}/take", response_model=TestTakeResponse)
async def get_test_to_take(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get test with questions for taking (without correct answers marked)"""
    test = await test_service.get_test_by_id(db, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )
    return test


@router.put("/{test_id}", response_model=TestDetailResponse)
async def update_test(
    test_id: int,
    test_data: TestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update test basic info (only by author)"""
    existing_test = await test_service.get_test_by_id(db, test_id)
    if not existing_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )
    if existing_test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own tests",
        )

    test = await test_service.update_test(db, test_id, test_data)
    return test


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete test (only by author)"""
    existing_test = await test_service.get_test_by_id(db, test_id)
    if not existing_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )
    if existing_test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own tests",
        )

    await test_service.delete_test(db, test_id)


# Question endpoints
@router.post("/{test_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_question_to_test(
    test_id: int,
    question_data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a question to test (only by author)"""
    test = await test_service.get_test_by_id(db, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )
    if test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add questions to your own tests",
        )

    return await test_service.add_question_to_test(db, test_id, question_data)


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update question (only by test author)"""
    existing_question = await test_service.get_question_with_test(db, question_id)
    if not existing_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    if existing_question.test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update questions in your own tests",
        )

    question = await test_service.update_question(db, question_id, question_data)
    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete question (only by test author)"""
    existing_question = await test_service.get_question_with_test(db, question_id)
    if not existing_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    if existing_question.test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete questions from your own tests",
        )

    await test_service.delete_question(db, question_id)


# Answer endpoints
@router.post("/questions/{question_id}/answers", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
async def add_answer_to_question(
    question_id: int,
    answer_data: AnswerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an answer to question (only by test author)"""
    existing_question = await test_service.get_question_with_test(db, question_id)
    if not existing_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    if existing_question.test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add answers to questions in your own tests",
        )

    answer = await test_service.add_answer_to_question(db, question_id, answer_data)
    return answer


@router.put("/answers/{answer_id}", response_model=AnswerResponse)
async def update_answer(
    answer_id: int,
    answer_data: AnswerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update answer (only by test author)"""
    existing_answer = await test_service.get_answer_with_test(db, answer_id)
    if not existing_answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
        )
    if existing_answer.question.test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update answers in your own tests",
        )

    answer = await test_service.update_answer(db, answer_id, answer_data)
    return answer


@router.delete("/answers/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_answer(
    answer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete answer (only by test author)"""
    existing_answer = await test_service.get_answer_with_test(db, answer_id)
    if not existing_answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
        )
    if existing_answer.question.test.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete answers from your own tests",
        )

    await test_service.delete_answer(db, answer_id)


# Test submission and grading
@router.post("/{test_id}/submit", response_model=TestResult)
async def submit_test(
    test_id: int,
    submission: TestSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit test answers and get results"""
    if submission.test_id != test_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test ID in URL and submission do not match",
        )

    result = await test_service.grade_test_submission(db, submission)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
        )

    return result
