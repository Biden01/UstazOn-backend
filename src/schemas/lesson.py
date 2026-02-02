"""
Pydantic schemas for lesson document endpoints
"""
from pydantic import BaseModel
from typing import Any


class LessonResponse(BaseModel):
    """Response for lesson generation and retrieval"""
    id: int
    content: dict[str, Any]

    model_config = {"from_attributes": True}
