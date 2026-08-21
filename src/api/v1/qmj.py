from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
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
    file_data: QMJFileCreate,
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

    qmj_file = await qmj_service.add_file_to_qmj(db, qmj_id, file_data, current_user.id)
    return qmj_file


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_qmj_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete QMJ file attachment (only by uploader or QMJ author)"""
    existing_file = await qmj_service.get_qmj_file_with_qmj(db, file_id)
    if not existing_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    is_uploader = existing_file.uploaded_by_id == current_user.id
    is_qmj_author = existing_file.qmj is not None and existing_file.qmj.author_id == current_user.id
    if not (is_uploader or is_qmj_author):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete files you uploaded or files attached to your own QMJ",
        )

    await qmj_service.delete_qmj_file(db, file_id)
