from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.subject import SubjectResponse, InstitutionTypeResponse


# Subscribe schemas
class SubscribeBase(BaseModel):
    user_id: int
    subject_id: int
    institution_type_id: int
    end_date: date


class SubscribeCreate(SubscribeBase):
    pass


class SubscribeUpdate(BaseModel):
    end_date: Optional[date] = None
    subject_id: Optional[int] = None
    institution_type_id: Optional[int] = None


class SubscribeResponse(SubscribeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    subject: Optional[SubjectResponse] = None
    institution_type: Optional[InstitutionTypeResponse] = None

    model_config = ConfigDict(from_attributes=True)


# PageAccess schemas
class PageAccessBase(BaseModel):
    url_pattern: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    protection_level: str = Field(..., pattern="^(public|auth_only|subscription_required|admin_only)$")
    requires_specific_subject: bool = False
    subject_id: Optional[int] = None
    institution_type_id: Optional[int] = None
    is_active: bool = True


class PageAccessCreate(PageAccessBase):
    pass


class PageAccessUpdate(BaseModel):
    url_pattern: Optional[str] = Field(None, min_length=1, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    protection_level: Optional[str] = Field(
        None, pattern="^(public|auth_only|subscription_required|admin_only)$"
    )
    requires_specific_subject: Optional[bool] = None
    subject_id: Optional[int] = None
    institution_type_id: Optional[int] = None
    is_active: Optional[bool] = None


class PageAccessResponse(PageAccessBase):
    id: int
    created_at: datetime
    updated_at: datetime
    subject: Optional[SubjectResponse] = None
    institution_type: Optional[InstitutionTypeResponse] = None

    model_config = ConfigDict(from_attributes=True)
