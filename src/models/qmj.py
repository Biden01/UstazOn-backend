from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Table,
)
from sqlalchemy.orm import relationship

from src.db.base import Base


# Association tables for many-to-many relationships
qmj_subject = Table(
    "qmj_subjects",
    Base.metadata,
    Column("qmj_id", Integer, ForeignKey("qmj.id", ondelete="CASCADE")),
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE")),
)

qmj_institution_type = Table(
    "qmj_institution_types",
    Base.metadata,
    Column("qmj_id", Integer, ForeignKey("qmj.id", ondelete="CASCADE")),
    Column("institution_type_id", Integer, ForeignKey("institution_types.id", ondelete="CASCADE")),
)


class QMJ(Base):
    """
    ҚМЖ (Қысқа мерзімді жоспар) - Short-term lesson plan / Краткосрочное планирование
    Calendar-thematic planning for teachers
    """
    __tablename__ = "qmj"

    id = Column(Integer, primary_key=True, index=True)

    # Educational metadata
    grade = Column(Integer, nullable=True, index=True)  # 1-11 класс (nullable для миграции старых данных)
    quarter = Column(Integer, nullable=True, index=True)  # 1-4 четверть (nullable для миграции старых данных)
    code = Column(String(50), nullable=True, index=True)  # Subject code

    # Lesson info
    title = Column(Text, nullable=False)  # Lesson title (changed from String(500) to Text)
    text = Column(Text, nullable=True)  # Learning objectives / Цели обучения
    hour = Column(Integer, default=1)  # Lesson duration in hours
    order = Column(Integer, default=0, index=True)  # Sequence number within quarter

    # Main file (if uploaded as single file)
    file = Column(String(500), nullable=True)

    # Author
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    author = relationship("User", foreign_keys=[author_id], backref="qmj_plans")

    # Many-to-many relationships
    subjects = relationship("Subject", secondary=qmj_subject, backref="qmj_plans")
    institution_types = relationship("InstitutionType", secondary=qmj_institution_type, backref="qmj_plans")

    # One-to-many relationships
    files = relationship("QMJFile", back_populates="qmj", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def has_files(self) -> bool:
        """Check if QMJ has attached files"""
        return bool(self.files)

    @property
    def files_count(self) -> int:
        """Count of attached files"""
        return len(self.files) if self.files else 0


class QMJFile(Base):
    """
    Файлы-приложения к ҚМЖ
    Multiple file attachments for lesson plans
    """
    __tablename__ = "qmj_files"

    id = Column(Integer, primary_key=True, index=True)

    # File info
    file = Column(String(500), nullable=False)  # File path
    file_size = Column(Integer, nullable=True)  # File size in bytes
    file_type = Column(String(10), nullable=True)  # Extension: PDF, DOC, DOCX, TXT, RTF

    # Foreign keys
    qmj_id = Column(Integer, ForeignKey("qmj.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    qmj = relationship("QMJ", back_populates="files")
    uploaded_by = relationship("User")

    # Timestamp
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    @property
    def file_size_formatted(self) -> str:
        """Format file size in human-readable format"""
        if not self.file_size:
            return "Unknown"

        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @property
    def file_icon_class(self) -> str:
        """Get CSS icon class based on file type"""
        if not self.file_type:
            return "fa-file"

        type_map = {
            "PDF": "fa-file-pdf",
            "DOC": "fa-file-word",
            "DOCX": "fa-file-word",
            "TXT": "fa-file-text",
            "RTF": "fa-file-text",
        }
        return type_map.get(self.file_type.upper(), "fa-file")
