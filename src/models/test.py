from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Float,
)
from sqlalchemy.orm import relationship

from src.db.base import Base


class DifficultyLevel(str, Enum):
    """Уровни сложности теста"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Test(Base):
    """
    Тест для учителей
    Educational test
    """

    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(200), nullable=False, index=True)
    subject = Column(String(200), nullable=False, index=True)

    # Author
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    user = relationship("User", foreign_keys=[user_id], backref="tests")

    # Test settings
    duration = Column(Integer, default=30, nullable=False)  # Duration in minutes
    difficulty = Column(String(10), default=DifficultyLevel.MEDIUM.value, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questions = relationship(
        "Question", back_populates="test", cascade="all, delete-orphan"
    )

    @property
    def questions_count(self) -> int:
        """Count of questions in this test"""
        return len(self.questions) if self.questions else 0


class Question(Base):
    """
    Вопрос в тесте
    Question in a test
    """

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)

    # Parent test
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    test = relationship("Test", back_populates="questions")

    # Question content
    text = Column(Text, nullable=False)  # Changed from String(500) to Text for long questions
    photo = Column(String(500), nullable=True)  # Path to question image
    video = Column(String(500), nullable=True)  # Path to question video

    # Order in test
    order = Column(Integer, default=0)  # For ordering questions

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    answers = relationship(
        "Answer", back_populates="question", cascade="all, delete-orphan"
    )

    @property
    def correct_answer(self) -> "Answer | None":
        """Get the correct answer for this question"""
        if not self.answers:
            return None
        for answer in self.answers:
            if answer.is_correct:
                return answer
        return None


class Answer(Base):
    """
    Ответ на вопрос
    Answer to a question
    """

    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)

    # Parent question
    question_id = Column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question = relationship("Question", back_populates="answers")

    # Answer content
    text = Column(String(500), nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    # Order in question
    order = Column(Integer, default=0)  # For ordering answers

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TestResult(Base):
    """
    Результат прохождения теста студентом
    Student test result with anti-cheat tracking
    """

    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)

    # Test reference
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    test = relationship("Test", backref="results")

    # Student info
    student_name = Column(String(200), nullable=False)
    group_name = Column(String(200), nullable=True)

    # Scores
    correct_answers = Column(Integer, default=0, nullable=False)
    total_questions = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)  # 0-100

    # Anti-cheat tracking
    warning_count = Column(Integer, default=0, nullable=False)  # Tab switches, focus loss
    attempt_count = Column(Integer, default=1, nullable=False)  # Number of attempts

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    @property
    def passed(self) -> bool:
        """Check if student passed (>= 70%)"""
        return self.percentage >= 70.0


class TestLink(Base):
    """
    Шаринг ссылка для теста
    Shareable test link with unique hash for groups
    """

    __tablename__ = "test_links"

    id = Column(Integer, primary_key=True, index=True)

    # Test reference
    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    test = relationship("Test", backref="links")

    # Link info
    unique_hash = Column(String(100), unique=True, nullable=False, index=True)
    group_name = Column(String(200), nullable=True)

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    max_attempts = Column(Integer, nullable=True)  # Null = unlimited
    expires_at = Column(DateTime, nullable=True)  # Null = never expires

    # Stats
    attempts_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        """Check if link is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if link is valid and can be used"""
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.max_attempts and self.attempts_count >= self.max_attempts:
            return False
        return True
