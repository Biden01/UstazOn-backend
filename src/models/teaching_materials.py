"""
Teaching materials models for storing generated lesson plans, tests, homework, and rubrics
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.user import User


class MaterialType(str, enum.Enum):
    """Type of teaching material"""
    LESSON_PLAN = "lesson_plan"
    TEST = "test"
    HOMEWORK = "homework"
    RUBRIC = "rubric"
    PRESENTATION = "presentation"
    LESSON = "lesson"


class DifficultyLevel(str, enum.Enum):
    """Difficulty level for tests and homework"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class TeachingMaterial(Base):
    """
    Generated teaching materials (lesson plans, tests, homework, rubrics)
    """
    __tablename__ = "teaching_materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Material type and metadata
    material_type: Mapped[MaterialType] = mapped_column(
        Enum(MaterialType, native_enum=False, length=20),
        nullable=False
    )

    # Common fields for all materials
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)  # Математика, Физика, etc.
    grade: Mapped[str] = mapped_column(String(50), nullable=False)  # "7 класс", "9 класс", etc.
    topic: Mapped[str] = mapped_column(String(300), nullable=False)

    # Content (JSON structure varies by material_type)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)

    # File path for presentations and other file-based materials
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Additional metadata
    ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Which AI model generated it
    difficulty_level: Mapped[DifficultyLevel | None] = mapped_column(
        Enum(DifficultyLevel, native_enum=False, length=20),
        nullable=True
    )

    # For tests and homework
    estimated_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # minutes
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Tags for search
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Usage stats
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    download_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="teaching_materials")
