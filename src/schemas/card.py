from datetime import datetime
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict

if TYPE_CHECKING:
    from src.schemas.subject import SubjectResponse, InstitutionTypeResponse


# CardTopic schemas
class CardTopicBase(BaseModel):
    topic: str = Field(..., max_length=255)


class CardTopicCreate(CardTopicBase):
    parent_topic_id: int | None = None


class CardTopicUpdate(BaseModel):
    topic: str | None = Field(None, max_length=255)
    parent_topic_id: int | None = None


class CardTopicSimple(CardTopicBase):
    """Card topic without children - used in Card responses"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_topic_id: int | None = None
    created_at: datetime


class CardTopicResponse(CardTopicBase):
    """Card topic with full hierarchy - used in topics API"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_topic_id: int | None = None
    created_at: datetime
    children: list["CardTopicResponse"] = []


# Card schemas
class CardBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    grade: int | None = Field(None, ge=1, le=11)
    quarter: int | None = Field(None, ge=1, le=4)
    topic_id: int | None = None
    window_id: int | None = None
    subject_card: str | None = Field(None, max_length=255)
    file_path: str | None = Field(None, max_length=500)
    url: str | None = Field(None, max_length=500)
    iframe: bool = True
    img1_url: str | None = Field(None, max_length=500)
    img2_url: str | None = Field(None, max_length=500)
    img3_url: str | None = Field(None, max_length=500)
    img4_url: str | None = Field(None, max_length=500)
    img5_url: str | None = Field(None, max_length=500)
    video1_url: str | None = Field(None, max_length=500)
    video1_file_path: str | None = Field(None, max_length=500)


class CardCreate(CardBase):
    subject_ids: list[int] = Field(default_factory=list)
    institution_type_ids: list[int] = Field(default_factory=list)


class CardUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    grade: int | None = Field(None, ge=1, le=11)
    quarter: int | None = Field(None, ge=1, le=4)
    topic_id: int | None = None
    window_id: int | None = None
    subject_card: str | None = Field(None, max_length=255)
    file_path: str | None = Field(None, max_length=500)
    url: str | None = Field(None, max_length=500)
    iframe: bool | None = None
    img1_url: str | None = Field(None, max_length=500)
    img2_url: str | None = Field(None, max_length=500)
    img3_url: str | None = Field(None, max_length=500)
    img4_url: str | None = Field(None, max_length=500)
    img5_url: str | None = Field(None, max_length=500)
    video1_url: str | None = Field(None, max_length=500)
    video1_file_path: str | None = Field(None, max_length=500)
    subject_ids: list[int] | None = None
    institution_type_ids: list[int] | None = None


class CardResponse(CardBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int | None
    created_at: datetime
    updated_at: datetime
    favorites_count: int

    # Nested relationships
    topic: CardTopicSimple | None = None


class CardListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    grade: int | None
    quarter: int | None
    author_id: int | None
    created_at: datetime
    favorites_count: int
    img1_url: str | None
    url: str | None = None
    file_path: str | None = None
    topic: CardTopicSimple | None = None
    window_id: int | None = None


class CardDetailResponse(CardResponse):
    """Extended response with full relationship data"""

    subjects: list["SubjectResponse"] = Field(default_factory=list)
    institution_types: list["InstitutionTypeResponse"] = Field(default_factory=list)


# Import actual models and rebuild to resolve forward references
def _rebuild_models():
    from src.schemas.subject import SubjectResponse, InstitutionTypeResponse
    CardTopicResponse.model_rebuild()  # Rebuild for recursive children
    CardDetailResponse.model_rebuild()


# Call rebuild when module is imported
_rebuild_models()
