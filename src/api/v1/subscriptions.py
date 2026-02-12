from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_current_superuser, get_db
from src.models.user import User
from src.schemas.subscription import (
    SubscribeCreate,
    SubscribeUpdate,
    SubscribeResponse,
    UserSubscriptionGrant,
)
from src.services import subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscribeResponse])
async def get_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Get list of all subscriptions (admin only)"""
    subscriptions = await subscription_service.get_all_subscriptions(
        db, active_only=active_only, skip=skip, limit=limit
    )
    return subscriptions


@router.get("/expired", response_model=list[SubscribeResponse])
async def get_expired_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Get list of expired subscriptions (admin only)"""
    subscriptions = await subscription_service.get_expired_subscriptions(
        db, skip=skip, limit=limit
    )
    return subscriptions


@router.get("/expiring-soon", response_model=list[SubscribeResponse])
async def get_expiring_soon_subscriptions(
    days: int = Query(7, ge=1, le=30),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Get list of subscriptions expiring soon (admin only)"""
    subscriptions = await subscription_service.get_expiring_soon_subscriptions(
        db, days=days, skip=skip, limit=limit
    )
    return subscriptions


@router.get("/{subscription_id}", response_model=SubscribeResponse)
async def get_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Get subscription by ID (admin only)"""
    subscription = await subscription_service.get_subscription_by_id(
        db, subscription_id
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )
    return subscription


@router.post("", response_model=SubscribeResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscribeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Create new subscription (admin only)"""
    subscription = await subscription_service.create_subscription(
        db,
        user_id=subscription_data.user_id,
        subject_id=subscription_data.subject_id,
        institution_type_id=subscription_data.institution_type_id,
        end_date=subscription_data.end_date,
    )
    return subscription


@router.post("/bulk", response_model=list[SubscribeResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_subscriptions(
    subscriptions_data: list[SubscribeCreate] = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Create multiple subscriptions at once (admin only)"""
    data_list = [
        {
            "user_id": sub.user_id,
            "subject_id": sub.subject_id,
            "institution_type_id": sub.institution_type_id,
            "end_date": sub.end_date,
        }
        for sub in subscriptions_data
    ]
    return await subscription_service.create_bulk_subscriptions(db, data_list)


@router.put("/{subscription_id}", response_model=SubscribeResponse)
async def update_subscription(
    subscription_id: int,
    subscription_data: SubscribeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Update subscription (admin only)"""
    subscription = await subscription_service.get_subscription_by_id(
        db, subscription_id
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )

    updated_subscription = await subscription_service.update_subscription(
        db,
        subscription,
        end_date=subscription_data.end_date,
        subject_id=subscription_data.subject_id,
        institution_type_id=subscription_data.institution_type_id,
    )
    return updated_subscription


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Delete subscription (admin only)"""
    subscription = await subscription_service.get_subscription_by_id(
        db, subscription_id
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )

    await subscription_service.delete_subscription(db, subscription)


@router.get("/users/{user_id}/subscriptions", response_model=list[SubscribeResponse])
async def get_user_subscriptions(
    user_id: int,
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Get all subscriptions for a user (admin only)"""
    subscriptions = await subscription_service.get_user_subscriptions(
        db, user_id, active_only=active_only, skip=skip, limit=limit
    )
    return subscriptions


@router.get("/subjects/{subject_id}/subscriptions", response_model=list[SubscribeResponse])
async def get_subject_subscriptions(
    subject_id: int,
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Get all subscriptions for a subject (admin only)"""
    subscriptions = await subscription_service.get_subject_subscriptions(
        db, subject_id, active_only=active_only, skip=skip, limit=limit
    )
    return subscriptions


@router.post("/users/{user_id}/subscriptions", response_model=list[SubscribeResponse])
async def grant_subscription_to_user(
    user_id: int,
    grant_data: UserSubscriptionGrant,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Grant a subscription to a user for a subject across multiple institution types"""
    subscriptions = await subscription_service.grant_user_subject_subscription(
        db,
        user_id=user_id,
        subject_id=grant_data.subject_id,
        institution_type_ids=grant_data.institution_type_ids,
        days=grant_data.days,
    )
    return subscriptions


@router.get("/me/subscriptions", response_model=list[SubscribeResponse])
async def get_my_subscriptions(
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's subscriptions"""
    subscriptions = await subscription_service.get_user_subscriptions(
        db, current_user.id, active_only=active_only, skip=skip, limit=limit
    )
    return subscriptions


@router.get("/me/check")
async def check_my_subscription(
    subject_id: int = Query(..., description="Subject ID to check subscription for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if current user has an active subscription for a subject"""
    # Admins/superusers always have access
    if current_user.is_admin or current_user.is_superuser:
        return {"has_subscription": True}

    has_sub = await subscription_service.check_user_has_active_subscription(
        db, current_user.id, subject_id
    )
    return {"has_subscription": has_sub}
