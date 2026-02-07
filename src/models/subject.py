from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship

from src.db.base import Base


# Association table for Subject <-> InstitutionType many-to-many
subject_institution_type = Table(
    "subject_institution_type",
    Base.metadata,
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE")),
    Column(
        "institution_type_id",
        Integer,
        ForeignKey("institution_types.id", ondelete="CASCADE"),
    ),
)


# Association table for Subject <-> Window many-to-many
subject_window = Table(
    "subject_window",
    Base.metadata,
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE")),
    Column("window_id", Integer, ForeignKey("windows.id", ondelete="CASCADE")),
)


class InstitutionType(Base):
    """
    Тип учреждения: Мектеп, Колледж, Университет и т.д.
    Institution type: School, College, University, etc.
    """

    __tablename__ = "institution_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # e.g., "Мектеп"
    code = Column(String(50), nullable=True, unique=True)  # e.g., "school"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subjects = relationship(
        "Subject", secondary=subject_institution_type, back_populates="institution_types"
    )
    subscriptions = relationship("Subscribe", back_populates="institution_type")


class Subject(Base):
    """
    Предмет: Математика, Физика, Химия и т.д.
    Subject: Mathematics, Physics, Chemistry, etc.
    """

    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Математика"
    code = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "math"

    # Images
    image_url = Column(String(500), nullable=True)
    hero_image_url = Column(String(500), nullable=True)
    image_file = Column(String(100), nullable=True)
    hero_image_file = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    institution_types = relationship(
        "InstitutionType",
        secondary=subject_institution_type,
        back_populates="subjects",
    )
    windows = relationship(
        "Window", secondary=subject_window, back_populates="subjects"
    )
    subscriptions = relationship("Subscribe", back_populates="subject")


class Template(Base):
    """
    Шаблон/категория материалов
    Template/category for materials
    """

    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code_name = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    windows = relationship("Window", back_populates="template")


class Window(Base):
    """
    Окно/раздел для группировки материалов
    Window/section for grouping materials
    """

    __tablename__ = "windows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    link = Column(String(255), nullable=True)
    nsub = Column(Boolean, default=False)  # requires subscription
    image_url = Column(String(500), nullable=True)
    image_file = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("Template", back_populates="windows")
    subjects = relationship("Subject", secondary=subject_window, back_populates="windows")
