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
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from src.db.base import Base


# Association tables for many-to-many relationships
game_subject = Table(
    "game_subjects",
    Base.metadata,
    Column("game_id", Integer, ForeignKey("games.id", ondelete="CASCADE")),
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE")),
)

game_institution_type = Table(
    "game_institution_types",
    Base.metadata,
    Column("game_id", Integer, ForeignKey("games.id", ondelete="CASCADE")),
    Column("institution_type_id", Integer, ForeignKey("institution_types.id", ondelete="CASCADE")),
)

game_category = Table(
    "game_categories_link",
    Base.metadata,
    Column("game_id", Integer, ForeignKey("games.id", ondelete="CASCADE")),
    Column("category_id", Integer, ForeignKey("game_categories.id", ondelete="CASCADE")),
)

game_favorites = Table(
    "game_favorites",
    Base.metadata,
    Column("game_id", Integer, ForeignKey("games.id", ondelete="CASCADE")),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
)


class GameType(str, Enum):
    """17 типов игр"""
    # Бесплатные игры
    QUIZ = "quiz"  # Викторина
    MATCH = "match"  # Соответствие
    FLASHCARDS = "flashcards"  # Флэш-карточки
    MEMORY = "memory"  # Мемори
    SPIN_WHEEL = "spin_wheel"  # Колесо фортуны
    FILL_BLANKS = "fill_blanks"  # Заполни пропуски
    DRAG_DROP = "drag_drop"  # Перетащи и брось
    GROUP_SORT = "group_sort"  # Сортировка по группам
    WORD_CLOUD = "word_cloud"  # Облако слов
    RANKING = "ranking"  # Рейтинг
    PUZZLE = "puzzle"  # Пазл
    TYPING = "typing"  # Скорость печати

    # Премиум игры
    WORDSEARCH = "wordsearch"  # Поиск слов (PREMIUM)
    CROSSWORD = "crossword"  # Кроссворд (PREMIUM)
    ANAGRAM = "anagram"  # Анаграммы (PREMIUM)
    MAZE_CHASE = "maze_chase"  # Лабиринт (PREMIUM)
    TIMELINE = "timeline"  # Временная шкала (PREMIUM)


class DifficultyLevel(str, Enum):
    """Уровни сложности"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ItemType(str, Enum):
    """Типы игровых элементов"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    PAIR = "pair"
    GROUP = "group"


class GameCategory(Base):
    """Категории игр"""
    __tablename__ = "game_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)  # HEX color
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    games = relationship("Game", secondary=game_category, back_populates="categories")


class GameTemplate(Base):
    """Шаблоны игр - 17 типов"""
    __tablename__ = "game_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String(100), nullable=False)
    game_type = Column(String(20), nullable=False, index=True)  # GameType enum value
    description = Column(Text, nullable=True)
    instruction = Column(Text, nullable=True)

    # Media
    preview_image = Column(String(500), nullable=True)
    icon = Column(String(50), nullable=True)

    # Constraints
    min_items = Column(Integer, default=1)
    max_items = Column(Integer, default=100)

    # Settings
    default_settings = Column(JSON, default=dict)  # Default game settings

    # Status
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    games = relationship("Game", back_populates="template")


class Game(Base):
    """Игровые экземпляры"""
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Educational metadata
    difficulty = Column(String(10), default=DifficultyLevel.MEDIUM.value)
    grade = Column(Integer, nullable=True, index=True)  # 1-11
    quarter = Column(Integer, nullable=True, index=True)  # 1-4

    # Game settings
    time_limit = Column(Integer, nullable=True)  # Seconds
    attempts_limit = Column(Integer, nullable=True)
    show_correct_answers = Column(Boolean, default=True)
    shuffle_items = Column(Boolean, default=True)

    # Publishing settings
    is_public = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    allow_embedding = Column(Boolean, default=True)
    password = Column(String(255), nullable=True)  # Optional password protection

    # Custom settings (JSON)
    settings = Column(JSON, default=dict)

    # Statistics
    views_count = Column(Integer, default=0)
    plays_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)

    # Relationships (ForeignKeys)
    template_id = Column(Integer, ForeignKey("game_templates.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    topic_id = Column(Integer, ForeignKey("card_topics.id"), nullable=True)

    template = relationship("GameTemplate", back_populates="games")
    author = relationship("User", foreign_keys=[author_id])
    topic = relationship("CardTopic")

    # Many-to-many relationships
    subjects = relationship("Subject", secondary=game_subject, backref="games")
    institution_types = relationship("InstitutionType", secondary=game_institution_type, backref="games")
    categories = relationship("GameCategory", secondary=game_category, back_populates="games")
    favorites = relationship("User", secondary=game_favorites, backref="favorite_games")

    # One-to-many relationships
    items = relationship("GameItem", back_populates="game", cascade="all, delete-orphan")
    results = relationship("GameResult", back_populates="game", cascade="all, delete-orphan")
    links = relationship("GameLink", back_populates="game", cascade="all, delete-orphan")
    ratings = relationship("GameRating", back_populates="game", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def favorites_count(self) -> int:
        return len(self.favorites) if self.favorites else 0

    @property
    def items_count(self) -> int:
        return len(self.items) if self.items else 0

    @property
    def average_rating(self) -> float:
        if not self.ratings:
            return 0.0
        return sum(r.rating for r in self.ratings) / len(self.ratings)


class GameItem(Base):
    """Элементы игры (вопросы, пары, группы и т.д.)"""
    __tablename__ = "game_items"

    id = Column(Integer, primary_key=True, index=True)

    # Item type
    item_type = Column(String(20), default=ItemType.TEXT.value)

    # Content
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    answer_options = Column(JSON, default=list)  # For multiple choice

    # Additional info
    hint = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)

    # Media files
    image = Column(String(500), nullable=True)
    audio = Column(String(500), nullable=True)
    video = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    # Game mechanics
    points = Column(Integer, default=1)
    time_limit = Column(Integer, nullable=True)  # Seconds for this item
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Extra data (game-specific JSON data)
    extra_data = Column(JSON, default=dict)

    # Foreign key
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    game = relationship("Game", back_populates="items")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GameResult(Base):
    """Результаты прохождения игр"""
    __tablename__ = "game_results"

    id = Column(Integer, primary_key=True, index=True)

    # Score
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    correct_answers = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)

    # Time tracking
    time_spent = Column(Integer, nullable=True)  # Seconds
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, default=datetime.utcnow)

    # Player info
    player_name = Column(String(255), nullable=True)
    player_email = Column(String(255), nullable=True)
    group_name = Column(String(255), nullable=True)

    # Detailed data
    answers_data = Column(JSON, default=dict)  # Full answer details

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Foreign keys
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    game = relationship("Game", back_populates="results")
    player = relationship("User")


class GameLink(Base):
    """Ссылки для шаринга игр"""
    __tablename__ = "game_links"

    id = Column(Integer, primary_key=True, index=True)

    # Link info
    unique_hash = Column(String(64), unique=True, nullable=False, index=True)
    group_name = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)

    # Settings
    expires_at = Column(DateTime, nullable=True)
    max_attempts = Column(Integer, nullable=True)
    attempts_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Foreign key
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    game = relationship("Game", back_populates="links")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def can_access(self) -> bool:
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.max_attempts and self.attempts_count >= self.max_attempts:
            return False
        return True


class GameRating(Base):
    """Рейтинги игр от пользователей"""
    __tablename__ = "game_ratings"
    __table_args__ = (UniqueConstraint("game_id", "user_id", name="uq_game_user_rating"),)

    id = Column(Integer, primary_key=True, index=True)

    # Rating
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)

    # Foreign keys
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    game = relationship("Game", back_populates="ratings")
    user = relationship("User")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
