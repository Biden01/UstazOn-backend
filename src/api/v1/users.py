from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_current_superuser, get_db
from src.models.user import User
from src.schemas.user import UserResponse, UserUpdate
from src.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


class UsersListResponse(BaseModel):
    items: list[UserResponse]
    total: int


@router.get("/list", response_model=UsersListResponse)
async def list_users(
    search: str = Query("", description="Search by IIN, name, or phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """List/search users (admin only)"""
    query = select(User)
    count_query = select(func.count(User.id))

    if search.strip():
        term = f"%{search.strip()}%"
        condition = or_(
            User.iin.ilike(term),
            User.name.ilike(term),
            User.phone.ilike(term),
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(User.id.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UsersListResponse(items=users, total=total)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_data.phone and user_data.phone != current_user.phone:
        existing_user = await user_service.get_user_by_phone(db, user_data.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Этот номер телефона уже используется",
            )

    updated_user = await user_service.update_user_profile(db, current_user, user_data)
    return updated_user
