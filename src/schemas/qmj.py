from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# QMJFile schemas
class QMJFileBase(BaseModel):
    file: str = Field(..., max_length=500)
    file_size: int | None = None
    file_type: str | None = Field(None, max_length=10)


class QMJFileCreate(BaseModel):
    file: str = Field(..., max_length=500)
    file_size: int | None = None
    file_type: str | None = Field(None, max_length=10)


class QMJFileResponse(QMJFileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    qmj_id: int
    uploaded_by_id: int | None
    uploaded_at: datetime
    file_size_formatted: str
    file_icon_class: str


# QMJ schemas
class QMJBase(BaseModel):
    grade: int = Field(..., ge=1, le=11)
    quarter: int = Field(..., ge=1, le=4)
    code: str | None = Field(None, max_length=50)
    title: str = Field(..., max_length=500)
    text: str | None = None
    hour: int = Field(default=1, ge=1)
    order: int = Field(default=0, ge=0)
    file: str | None = Field(None, max_length=500)


class QMJCreate(QMJBase):
    subject_ids: list[int] = Field(default_factory=list)
    institution_type_ids: list[int] = Field(default_factory=list)


class QMJUpdate(BaseModel):
    grade: int | None = Field(None, ge=1, le=11)
    quarter: int | None = Field(None, ge=1, le=4)
    code: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=500)
    text: str | None = None
    hour: int | None = Field(None, ge=1)
    order: int | None = Field(None, ge=0)
    file: str | None = Field(None, max_length=500)
    subject_ids: list[int] | None = None
    institution_type_ids: list[int] | None = None


class QMJResponse(QMJBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int | None
    created_at: datetime
    updated_at: datetime
    has_files: bool
    files_count: int


class QMJDetailResponse(QMJResponse):
    """Detailed QMJ response with files and relationships"""

    files: list[QMJFileResponse] = Field(default_factory=list)


class QMJListItem(BaseModel):
    """Simplified QMJ for list views"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    grade: int
    quarter: int
    code: str | None
    title: str
    hour: int
    order: int
    author_id: int | None
    files_count: int
    created_at: datetime
