import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.core.storage import save_document, get_file_extension
from src.models.teaching_materials import TeachingMaterial, MaterialType
from src.models.user import User
from src.schemas.qmj import (
    QMJCreate,
    QMJUpdate,
    QMJResponse,
    QMJDetailResponse,
    QMJListItem,
    QMJFileCreate,
    QMJFileResponse,
)
from src.services import qmj_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_qmj(
    subject: str = Form(...),
    grade: str = Form(...),
    topic: str = Form(...),
    language: str = Form("kk"),
    model: str = Form("gemini-2.5-flash"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI-generate a structured QMJ (Қысқа мерзімді жоспар / Краткосрочный план).

    Generates a full short-term lesson plan following the official Kazakhstan
    education standard format and saves it to the database.

    Returns the teaching material ID and the full JSON content.
    """
    from src.api.v1.ai import check_rate_limit, log_generation_event

    try:
        check_rate_limit(current_user.id, "test")
        check_rate_limit(current_user.id, "global")

        if language not in ("kk", "ru"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="language must be 'kk' or 'ru'",
            )

        from src.services.qmj_ai_service import generate_qmj as _generate

        result = await _generate(
            db=db,
            user_id=current_user.id,
            subject=subject,
            grade=grade,
            topic=topic,
            language=language,
            model=model,
        )

        log_generation_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "qmj_generation",
            "user_id": current_user.id,
            "parameters": {
                "subject": subject,
                "grade": grade,
                "topic": topic,
                "language": language,
            },
            "ai_provider": model,
            "material_id": result["id"],
            "status": "success",
        })

        return result

    except HTTPException:
        raise
    except Exception as e:
        log_generation_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "qmj_generation_error",
            "user_id": current_user.id,
            "error": str(e),
            "status": "failed",
        })
        logger.error(f"Error generating QMJ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate QMJ: {str(e)}",
        )


@router.get("/ai/{material_id}")
async def get_ai_qmj(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve an AI-generated QMJ by its TeachingMaterial ID.

    Returns the full structured QMJ JSON content.
    """
    result = await db.execute(
        select(TeachingMaterial).where(
            TeachingMaterial.id == material_id,
            TeachingMaterial.material_type == MaterialType.QMJ,
        )
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI-generated QMJ not found",
        )

    material.view_count += 1
    await db.commit()

    return {"id": material.id, "content": material.content}


@router.get("/", response_model=list[QMJListItem])
async def get_qmj_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    grade: int | None = Query(None, ge=1, le=11),
    quarter: int | None = Query(None, ge=1, le=4),
    code: str | None = None,
    author_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get QMJ list with optional filters"""
    return await qmj_service.get_qmj_list(
        db, skip=skip, limit=limit, grade=grade, quarter=quarter, code=code, author_id=author_id
    )


@router.get("/my", response_model=list[QMJListItem])
async def get_my_qmj(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    grade: int | None = Query(None, ge=1, le=11),
    quarter: int | None = Query(None, ge=1, le=4),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get QMJ created by current user"""
    return await qmj_service.get_qmj_list(
        db, skip=skip, limit=limit, grade=grade, quarter=quarter, author_id=current_user.id
    )


@router.get("/quarter/{quarter}", response_model=list[QMJListItem])
async def get_qmj_by_quarter(
    quarter: int,
    grade: int | None = Query(None, ge=1, le=11),
    code: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all QMJ for a specific quarter"""
    if quarter < 1 or quarter > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quarter must be between 1 and 4",
        )

    return await qmj_service.get_qmj_by_quarter(db, quarter, grade=grade, code=code)


@router.post("/", response_model=QMJDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_qmj(
    qmj_data: QMJCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new QMJ (authenticated users only)"""
    return await qmj_service.create_qmj(db, qmj_data, current_user.id)


@router.get("/{qmj_id}", response_model=QMJDetailResponse)
async def get_qmj(
    qmj_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get QMJ by ID with all details"""
    qmj = await qmj_service.get_qmj_by_id(db, qmj_id)
    if not qmj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="QMJ not found"
        )
    return qmj


@router.put("/{qmj_id}", response_model=QMJDetailResponse)
async def update_qmj(
    qmj_id: int,
    qmj_data: QMJUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update QMJ (only by author)"""
    existing_qmj = await qmj_service.get_qmj_by_id(db, qmj_id)
    if not existing_qmj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="QMJ not found"
        )
    if existing_qmj.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own QMJ",
        )

    qmj = await qmj_service.update_qmj(db, qmj_id, qmj_data)
    return qmj


@router.delete("/{qmj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_qmj(
    qmj_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete QMJ (only by author)"""
    existing_qmj = await qmj_service.get_qmj_by_id(db, qmj_id)
    if not existing_qmj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="QMJ not found"
        )
    if existing_qmj.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own QMJ",
        )

    await qmj_service.delete_qmj(db, qmj_id)


# QMJ File endpoints
@router.post("/{qmj_id}/files", response_model=QMJFileResponse, status_code=status.HTTP_201_CREATED)
async def add_file_to_qmj(
    qmj_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add file attachment to QMJ"""
    # Check if QMJ exists and user is the author
    qmj = await qmj_service.get_qmj_by_id(db, qmj_id)
    if not qmj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="QMJ not found"
        )
    if qmj.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add files to your own QMJ",
        )

    try:
        file_path = await save_document(file)
        file_size = file.size
        file_type = get_file_extension(file.filename or "").lstrip(".")
        file_data = QMJFileCreate(file=file_path, file_size=file_size, file_type=file_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    qmj_file = await qmj_service.add_file_to_qmj(db, qmj_id, file_data, current_user.id)
    return qmj_file


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_qmj_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete QMJ file attachment (only by uploader or QMJ author)"""
    # TODO: Add authorization check
    success = await qmj_service.delete_qmj_file(db, file_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
