from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Table,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from src.db.base import Base


# Association table for Card <-> Subject many-to-many
card_subject = Table(
    "card_subject",
    Base.metadata,
    Column("card_id", Integer, ForeignKey("cards.id", ondelete="CASCADE")),
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE")),
)


# Association table for Card <-> InstitutionType many-to-many
card_institution_type = Table(
    "card_institution_type",
    Base.metadata,
    Column("card_id", Integer, ForeignKey("cards.id", ondelete="CASCADE")),
    Column(
        "institution_type_id",
        Integer,
        ForeignKey("institution_types.id", ondelete="CASCADE"),
    ),
)


# Association table for Card favorites (User <-> Card many-to-many)
card_favorites = Table(
    "card_favorites",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("card_id", Integer, ForeignKey("cards.id", ondelete="CASCADE")),
)


class CardTopic(Base):
    """
    Тема урока/материала (древовидная структура)
    Topic for educational materials (tree structure)
    """

    __tablename__ = "card_topics"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255), nullable=False, index=True)
    parent_topic_id = Column(Integer, ForeignKey("card_topics.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cards = relationship("Card", back_populates="topic")
    parent = relationship("CardTopic", remote_side=[id], back_populates="children")
    children = relationship("CardTopic", back_populates="parent", cascade="all, delete-orphan")


class Card(Base):
    """
    Учебный материал (карточка)
    Educational material card for teachers
    """

    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)

    # Author and favorites
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    author = relationship("User", foreign_keys=[author_id])
    favorites = relationship(
        "User", secondary=card_favorites, backref="favorite_cards"
    )

    # Basic info
    name = Column(Text, nullable=False)  # Changed from String(255) to Text for long names
    description = Column(Text, nullable=True)

    # Grade and quarter
    grade = Column(Integer, nullable=True, index=True)  # Класс: 1-11
    quarter = Column(Integer, nullable=True, index=True)  # Четверть: 1-4

    # Topic
    topic_id = Column(Integer, ForeignKey("card_topics.id"), nullable=True)
    topic = relationship("CardTopic", back_populates="cards")

    # Window (category/section)
    window_id = Column(Integer, ForeignKey("windows.id"), nullable=True)
    window = relationship("Window")

    # Relations
    subjects = relationship("Subject", secondary=card_subject, backref="cards")
    institution_types = relationship(
        "InstitutionType", secondary=card_institution_type, backref="cards"
    )

    # Subject codes (comma-separated for quick access)
    subject_card = Column(String(255), nullable=True)  # e.g., "math,physics"

    # Files and URLs
    file_path = Column(String(500), nullable=True)  # Path to uploaded file
    url = Column(String(500), nullable=True)  # External link or iframe URL
    iframe = Column(Boolean, default=True)  # Use iframe for embedding

    # Images (up to 5 images - thumbnails from PDF or screenshots)
    img1_url = Column(String(500), nullable=True)
    img2_url = Column(String(500), nullable=True)
    img3_url = Column(String(500), nullable=True)
    img4_url = Column(String(500), nullable=True)
    img5_url = Column(String(500), nullable=True)

    # Video
    video1_url = Column(String(500), nullable=True)
    video1_file_path = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for better search performance
    __table_args__ = (
        Index("ix_cards_grade_quarter", "grade", "quarter"),
        Index("ix_cards_author_created", "author_id", "created_at"),
    )

    @property
    def favorites_count(self) -> int:
        """Count of users who favorited this card"""
        return len(self.favorites) if self.favorites else 0
