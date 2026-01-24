from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from src.models.test import DifficultyLevel


# Answer schemas
class AnswerBase(BaseModel):
    text: str = Field(..., max_length=500)
    is_correct: bool = False
    order: int = 0


class AnswerCreate(AnswerBase):
    pass


class AnswerUpdate(BaseModel):
    text: str | None = Field(None, max_length=500)
    is_correct: bool | None = None
    order: int | None = None


class AnswerResponse(AnswerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    created_at: datetime
    updated_at: datetime


class AnswerPublicResponse(BaseModel):
    """Public answer response (without is_correct for test-takers)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    order: int


# Question schemas
class QuestionBase(BaseModel):
    text: str = Field(..., max_length=500)
    photo: str | None = Field(None, max_length=500)
    video: str | None = Field(None, max_length=500)
    order: int = 0


class QuestionCreate(QuestionBase):
    answers: list[AnswerCreate] = Field(..., min_length=2)


class QuestionUpdate(BaseModel):
    text: str | None = Field(None, max_length=500)
    photo: str | None = Field(None, max_length=500)
    video: str | None = Field(None, max_length=500)
    order: int | None = None


class QuestionResponse(QuestionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_id: int
    answers: list[AnswerResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class QuestionPublicResponse(BaseModel):
    """Public question response (for test-takers, without correct answers)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    photo: str | None
    video: str | None
    order: int
    answers: list[AnswerPublicResponse] = Field(default_factory=list)


# Test schemas
class TestBase(BaseModel):
    title: str = Field(..., max_length=200)
    subject: str = Field(..., max_length=200)
    duration: int = Field(default=30, ge=1, le=180)  # 1-180 minutes
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM


class TestCreate(TestBase):
    questions: list[QuestionCreate] = Field(..., min_length=1)


class TestUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    subject: str | None = Field(None, max_length=200)
    duration: int | None = Field(None, ge=1, le=180)
    difficulty: DifficultyLevel | None = None


class TestResponse(TestBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    questions_count: int
    created_at: datetime
    updated_at: datetime


class TestDetailResponse(TestResponse):
    """Detailed test response with all questions and answers"""

    questions: list[QuestionResponse] = Field(default_factory=list)


class TestPublicResponse(BaseModel):
    """Public test response for test-takers"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subject: str
    duration: int
    difficulty: str
    questions_count: int


class TestTakeResponse(TestPublicResponse):
    """Test response when taking a test (with questions but without correct answers)"""

    questions: list[QuestionPublicResponse] = Field(default_factory=list)


# Test submission schemas
class AnswerSubmission(BaseModel):
    """User's answer to a question"""

    question_id: int
    answer_id: int


class TestSubmission(BaseModel):
    """User's full test submission"""

    test_id: int
    answers: list[AnswerSubmission]


class TestResult(BaseModel):
    """Test result after grading"""

    test_id: int
    total_questions: int
    correct_answers: int
    score_percentage: float
    passed: bool  # True if score >= 70%
