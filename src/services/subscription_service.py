from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from src.models.subscription import Subscribe, PageAccess
from src.models.user import User
from src.models.subject import Subject, InstitutionType


async def create_subscription(
    db: AsyncSession,
    user_id: int,
    subject_id: int,
    institution_type_id: int,
    end_date: date,
) -> Subscribe:
    subscription = Subscribe(
        user_id=user_id,
        subject_id=subject_id,
        institution_type_id=institution_type_id,
        end_date=end_date,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def get_subscription_by_id(
    db: AsyncSession,
    subscription_id: int,
) -> Optional[Subscribe]:
    result = await db.execute(
        select(Subscribe)
        .options(
            selectinload(Subscribe.user),
            selectinload(Subscribe.subject),
            selectinload(Subscribe.institution_type),
        )
        .where(Subscribe.id == subscription_id)
    )
    return result.scalar_one_or_none()


async def get_user_subscriptions(
    db: AsyncSession,
    user_id: int,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscribe]:
    query = (
        select(Subscribe)
        .options(
            selectinload(Subscribe.subject),
            selectinload(Subscribe.institution_type),
        )
        .where(Subscribe.user_id == user_id)
        .order_by(Subscribe.end_date.desc())
    )

    if active_only:
        query = query.where(Subscribe.end_date >= date.today())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_subject_subscriptions(
    db: AsyncSession,
    subject_id: int,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscribe]:
    query = (
        select(Subscribe)
        .options(
            selectinload(Subscribe.user),
            selectinload(Subscribe.institution_type),
        )
        .where(Subscribe.subject_id == subject_id)
        .order_by(Subscribe.end_date.desc())
    )

    if active_only:
        query = query.where(Subscribe.end_date >= date.today())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_subscriptions(
    db: AsyncSession,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscribe]:
    query = (
        select(Subscribe)
        .options(
            selectinload(Subscribe.user),
            selectinload(Subscribe.subject),
            selectinload(Subscribe.institution_type),
        )
        .order_by(Subscribe.created_at.desc())
    )

    if active_only:
        query = query.where(Subscribe.end_date >= date.today())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_subscription(
    db: AsyncSession,
    subscription: Subscribe,
    end_date: Optional[date] = None,
    subject_id: Optional[int] = None,
    institution_type_id: Optional[int] = None,
) -> Subscribe:
    if end_date is not None:
        subscription.end_date = end_date
    if subject_id is not None:
        subscription.subject_id = subject_id
    if institution_type_id is not None:
        subscription.institution_type_id = institution_type_id

    subscription.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def delete_subscription(
    db: AsyncSession,
    subscription: Subscribe,
) -> None:
    await db.delete(subscription)
    await db.commit()


async def check_user_has_active_subscription(
    db: AsyncSession,
    user_id: int,
    subject_id: int,
) -> bool:
    result = await db.execute(
        select(Subscribe).where(
            and_(
                Subscribe.user_id == user_id,
                Subscribe.subject_id == subject_id,
                Subscribe.end_date >= date.today(),
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def get_user_subscription_for_subject(
    db: AsyncSession,
    user_id: int,
    subject_id: int,
) -> Optional[Subscribe]:
    result = await db.execute(
        select(Subscribe)
        .options(
            selectinload(Subscribe.subject),
            selectinload(Subscribe.institution_type),
        )
        .where(
            and_(
                Subscribe.user_id == user_id,
                Subscribe.subject_id == subject_id,
            )
        )
        .order_by(Subscribe.end_date.desc())
    )
    return result.scalar_one_or_none()


async def get_expired_subscriptions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscribe]:
    result = await db.execute(
        select(Subscribe)
        .options(
            selectinload(Subscribe.user),
            selectinload(Subscribe.subject),
            selectinload(Subscribe.institution_type),
        )
        .where(Subscribe.end_date < date.today())
        .order_by(Subscribe.end_date.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_active_user_subscriptions(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscribe]:
    return await get_user_subscriptions(
        db, user_id, active_only=True, skip=skip, limit=limit
    )


async def get_expiring_soon_subscriptions(
    db: AsyncSession,
    days: int = 7,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscribe]:
    from sqlalchemy import func
    from datetime import timedelta

    result = await db.execute(
        select(Subscribe)
        .options(
            selectinload(Subscribe.user),
            selectinload(Subscribe.subject),
            selectinload(Subscribe.institution_type),
        )
        .where(
            and_(
                Subscribe.end_date >= date.today(),
                Subscribe.end_date <= date.today() + timedelta(days=days),
            )
        )
        .order_by(Subscribe.end_date.asc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_bulk_subscriptions(
    db: AsyncSession,
    subscriptions_data: list[dict],
) -> List[Subscribe]:
    """
    Create multiple subscriptions in a single transaction
    """
    subscriptions = []
    for data in subscriptions_data:
        subscription = Subscribe(
            user_id=data["user_id"],
            subject_id=data["subject_id"],
            institution_type_id=data["institution_type_id"],
            end_date=data["end_date"],
        )
        db.add(subscription)
        subscriptions.append(subscription)
    
    await db.commit()
    for sub in subscriptions:
        await db.refresh(sub)
    return subscriptions


async def grant_user_subject_subscription(
    db: AsyncSession,
    user_id: int,
    subject_id: int,
    institution_type_ids: List[int],
    days: int = 30,
) -> List[Subscribe]:
    """
    Grant a subscription to a user for a subject across multiple institution types.
    Default duration is 30 days.
    """
    from datetime import timedelta

    end_date = date.today() + timedelta(days=days)
    subscriptions = []

    for institution_type_id in institution_type_ids:
        existing = await db.execute(
            select(Subscribe).where(
                and_(
                    Subscribe.user_id == user_id,
                    Subscribe.subject_id == subject_id,
                    Subscribe.institution_type_id == institution_type_id,
                    Subscribe.end_date >= date.today(),
                )
            )
        )
        existing_sub = existing.scalar_one_or_none()

        if existing_sub:
            existing_sub.end_date = max(existing_sub.end_date, end_date)
            existing_sub.updated_at = datetime.utcnow()
            subscriptions.append(existing_sub)
        else:
            subscription = Subscribe(
                user_id=user_id,
                subject_id=subject_id,
                institution_type_id=institution_type_id,
                end_date=end_date,
            )
            db.add(subscription)
            subscriptions.append(subscription)

    await db.commit()
    for sub in subscriptions:
        await db.refresh(sub)
    return subscriptions
