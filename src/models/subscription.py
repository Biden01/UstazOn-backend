from datetime import datetime, date

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date, Text
from sqlalchemy.orm import relationship

from src.db.base import Base


class Subscribe(Base):
    """
    Подписка пользователя на предмет
    User subscription to subject with access control
    """

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    institution_type_id = Column(
        Integer, ForeignKey("institution_types.id", ondelete="CASCADE"), nullable=False
    )
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    subject = relationship("Subject", back_populates="subscriptions")
    institution_type = relationship("InstitutionType", back_populates="subscriptions")

    @property
    def is_active(self) -> bool:
        """Check if subscription is still active"""
        return self.end_date >= date.today()


class PageAccess(Base):
    """
    Контроль доступа к URL паттернам
    URL pattern-based access control
    """

    __tablename__ = "page_access"

    # Protection levels
    PROTECTION_PUBLIC = "public"
    PROTECTION_AUTH_ONLY = "auth_only"
    PROTECTION_SUBSCRIPTION = "subscription_required"
    PROTECTION_ADMIN = "admin_only"

    PROTECTION_LEVELS = [
        PROTECTION_PUBLIC,
        PROTECTION_AUTH_ONLY,
        PROTECTION_SUBSCRIPTION,
        PROTECTION_ADMIN,
    ]

    id = Column(Integer, primary_key=True, index=True)
    url_pattern = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    protection_level = Column(
        String(50), nullable=False, default=PROTECTION_PUBLIC, index=True
    )

    # Optional: require specific subject/institution type
    requires_specific_subject = Column(Boolean, default=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    institution_type_id = Column(Integer, ForeignKey("institution_types.id"), nullable=True)

    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subject = relationship("Subject")
    institution_type = relationship("InstitutionType")
