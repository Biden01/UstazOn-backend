"""
Lesson document API endpoints.

POST /lessons/generate  — AI-generate a structured lesson and save to DB
GET  /lessons/{id}      — Retrieve a saved lesson by ID
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.teaching_materials import TeachingMaterial, MaterialType
from src.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_lesson(
    subject: str = Form(...),
    grade: str = Form(...),
    topic: str = Form(...),
    language: str = Form("kk"),
    question_count: int = Form(10),
    difficulty: str = Form("medium"),
    model: str = Form("gemini-2.5-flash"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a structured lesson document using AI.

    The lesson includes: heading, theory blocks, vocabulary,
    a multiple-choice test (saved as a real Test entity), and open questions.

    Returns the lesson ID and the full JSON content.
    """
    from src.api.v1.ai import check_rate_limit, log_generation_event

    try:
        check_rate_limit(current_user.id, "test")
        check_rate_limit(current_user.id, "global")

        if question_count < 5 or question_count > 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="question_count must be between 5 and 50",
            )

        if difficulty not in ("easy", "medium", "hard"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="difficulty must be 'easy', 'medium', or 'hard'",
            )

        if language not in ("kk", "ru"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="language must be 'kk' or 'ru'",
            )

        from src.services.lesson_service import generate_lesson as _generate

        result = await _generate(
            db=db,
            user_id=current_user.id,
            subject=subject,
            grade=grade,
            topic=topic,
            language=language,
            question_count=question_count,
            difficulty=difficulty,
            model=model,
        )

        log_generation_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "lesson_generation",
            "user_id": current_user.id,
            "parameters": {
                "subject": subject,
                "grade": grade,
                "topic": topic,
                "language": language,
                "question_count": question_count,
                "difficulty": difficulty,
            },
            "ai_provider": model,
            "lesson_id": result["id"],
            "status": "success",
        })

        return result

    except HTTPException:
        raise
    except Exception as e:
        log_generation_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "lesson_generation_error",
            "user_id": current_user.id,
            "error": str(e),
            "status": "failed",
        })
        logger.error(f"Error generating lesson: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate lesson: {str(e)}",
        )


@router.get("/{lesson_id}")
async def get_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a lesson document by ID.

    Returns the full lesson JSON structure with meta, layout, and blocks.
    """
    result = await db.execute(
        select(TeachingMaterial).where(
            TeachingMaterial.id == lesson_id,
            TeachingMaterial.material_type == MaterialType.LESSON,
        )
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    # Increment view count
    material.view_count += 1
    await db.commit()

    return {"id": material.id, "content": material.content}
