from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Optional

class PresentationSlide(BaseModel):
    slide_number: int = Field(ge=1)
    title: str = Field(min_length=3, max_length=100)
    content: List[str] = Field(default_factory=list, min_length=0, max_length=10)
    image_query: str = Field(min_length=2, max_length=50, pattern=r'^[a-zA-Z0-9 ]+$')
    notes: Optional[str] = Field(default="", max_length=500)

    class Config:
        extra = "forbid"

class PresentationData(BaseModel):
    title: str = Field(min_length=5, max_length=100)
    slides: List[PresentationSlide] = Field(min_length=3, max_length=30)

    class Config:
        extra = "forbid"

class QuestionOption(BaseModel):
    label: str = Field(pattern=r'^[A-D]$')
    text: str = Field(min_length=1, max_length=200)

    class Config:
        extra = "forbid"

class TestQuestion(BaseModel):
    question_number: int = Field(ge=1)
    question_text: str = Field(min_length=10, max_length=500)
    options: List[QuestionOption] = Field(min_length=4, max_length=4)
    correct_answer: str = Field(pattern=r'^[A-D]$')

    class Config:
        extra = "forbid"

    @field_validator('correct_answer')
    @classmethod
    def validate_correct_answer(cls, v, info: ValidationInfo):
        if info.data and 'options' in info.data:
            labels = [opt.label for opt in info.data['options']]
            if v not in labels:
                raise ValueError("correct_answer must match one of the option labels")
        return v

class TestData(BaseModel):
    title: str = Field(min_length=5, max_length=100)
    instructions: Optional[str] = Field(default=None, max_length=200)
    questions: List[TestQuestion] = Field(min_length=5, max_length=50)

    class Config:
        extra = "forbid"

class PresentationGenerateResponse(BaseModel):
    material_id: int
    file_url: str

    class Config:
        extra = "forbid"


class GammaPresentationResponse(BaseModel):
    id: int
    gamma_document_id: str
    status: str

    class Config:
        extra = "forbid"


class PresentationStatusResponse(BaseModel):
    id: int
    status: str
    gamma_url: Optional[str] = None

    class Config:
        extra = "forbid"
