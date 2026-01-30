"""
Teaching Materials API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.teaching_materials import TeachingMaterial, MaterialType
from src.api.deps import get_current_user
from src.models.user import User
from src.db.session import get_db
from src.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/my")
async def get_my_teaching_materials(
    material_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's teaching materials

    Args:
        material_type: Optional filter by material type (presentation, lesson_plan, test, etc.)

    Returns:
        List of teaching materials
    """
    try:
        query = select(TeachingMaterial).where(
            TeachingMaterial.user_id == current_user.id
        )

        if material_type:
            query = query.where(TeachingMaterial.material_type == material_type)

        query = query.order_by(TeachingMaterial.created_at.desc())

        result = await db.execute(query)
        materials = result.scalars().all()

        result = []
        for m in materials:
            item = {
                "id": m.id,
                "title": m.title,
                "subject": m.subject,
                "grade": m.grade,
                "topic": m.topic,
                "material_type": m.material_type,
                "file_url": f"{settings.MEDIA_URL}{m.file_path}" if m.file_path else None,
                "created_at": m.created_at.isoformat(),
            }
            # For presentations: include gamma_url and generation status
            if m.material_type == MaterialType.PRESENTATION and isinstance(m.content, dict):
                item["gamma_url"] = m.content.get("gamma_url")
                item["status"] = m.content.get("status", "generating")
            result.append(item)
        return result

    except Exception as e:
        logger.error(f"Error fetching teaching materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch teaching materials"
        )
