"""
Teaching Materials API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sql_delete

from src.models.teaching_materials import TeachingMaterial, MaterialType
from src.api.deps import get_current_user, get_current_superuser
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
                item["status"] = m.content.get("status", "pending")
            result.append(item)
        return result

    except Exception as e:
        logger.error(f"Error fetching teaching materials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch teaching materials"
        )


@router.get("/")
async def get_all_teaching_materials(
    material_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Admin: get all teaching materials"""
    query = select(
        TeachingMaterial.id,
        TeachingMaterial.user_id,
        TeachingMaterial.material_type,
        TeachingMaterial.title,
        TeachingMaterial.subject,
        TeachingMaterial.grade,
        TeachingMaterial.topic,
        TeachingMaterial.content,
        TeachingMaterial.ai_model,
        TeachingMaterial.difficulty_level,
        TeachingMaterial.estimated_time,
        TeachingMaterial.question_count,
        TeachingMaterial.view_count,
        TeachingMaterial.download_count,
        TeachingMaterial.created_at,
    )

    if material_type:
        query = query.where(TeachingMaterial.material_type == material_type)

    query = query.order_by(TeachingMaterial.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    materials = result.all()

    count_query = select(func.count(TeachingMaterial.id))
    if material_type:
        count_query = count_query.where(TeachingMaterial.material_type == material_type)
    total = (await db.execute(count_query)).scalar() or 0

    items = []
    for m in materials:
        mt = m.material_type.value if isinstance(m.material_type, MaterialType) else m.material_type
        item = {
            "id": m.id,
            "title": m.title,
            "subject": m.subject,
            "grade": m.grade,
            "topic": m.topic,
            "material_type": mt,
            "ai_model": m.ai_model,
            "difficulty_level": m.difficulty_level,
            "estimated_time": m.estimated_time,
            "question_count": m.question_count,
            "view_count": m.view_count,
            "download_count": m.download_count,
            "user_id": m.user_id,
            "file_url": None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        if mt == "presentation" and isinstance(m.content, dict):
            item["gamma_url"] = m.content.get("gamma_url")
            item["status"] = m.content.get("status", "pending")
        items.append(item)
    return {"items": items, "total": total}


@router.delete("/{material_id}")
async def delete_teaching_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a teaching material (owner or admin)"""
    result = await db.execute(
        select(TeachingMaterial.id, TeachingMaterial.user_id).where(TeachingMaterial.id == material_id)
    )
    material = result.one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    if material.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.execute(
        sql_delete(TeachingMaterial).where(TeachingMaterial.id == material_id)
    )
    await db.commit()
    return {"detail": "Deleted"}
