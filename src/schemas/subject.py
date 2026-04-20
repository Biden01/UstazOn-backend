from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# InstitutionType schemas
class InstitutionTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=50)


class InstitutionTypeCreate(InstitutionTypeBase):
    pass


class InstitutionTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=50)


class InstitutionTypeResponse(InstitutionTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Subject schemas
class SubjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    hero_image_url: Optional[str] = Field(None, max_length=500)


class SubjectCreate(SubjectBase):
    institution_type_ids: list[int] = Field(default_factory=list)
    window_ids: list[int] = Field(default_factory=list)


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    hero_image_url: Optional[str] = Field(None, max_length=500)
    institution_type_ids: Optional[list[int]] = None
    window_ids: Optional[list[int]] = None


class SubjectResponse(SubjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    institution_types: list[InstitutionTypeResponse] = Field(default_factory=list)
    windows: list["WindowResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Template schemas
class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code_name: str = Field(..., min_length=1, max_length=50)


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code_name: Optional[str] = Field(None, min_length=1, max_length=50)


class TemplateResponse(TemplateBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Window schemas
class WindowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    template_id: Optional[int] = None
    link: Optional[str] = Field(None, max_length=255)
    nsub: bool = False  # requires subscription
    image_url: Optional[str] = Field(None, max_length=500)


class WindowCreate(WindowBase):
    subject_ids: list[int] = Field(default_factory=list)


class WindowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    template_id: Optional[int] = None
    link: Optional[str] = Field(None, max_length=255)
    nsub: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=500)
    subject_ids: Optional[list[int]] = None


class WindowResponse(WindowBase):
    id: int
    created_at: datetime
    template: Optional[TemplateResponse] = None

    model_config = ConfigDict(from_attributes=True)
