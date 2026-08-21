from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash, verify_and_upgrade_password
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate


async def get_user_by_iin(db: AsyncSession, iin: str) -> User | None:
    result = await db.execute(select(User).where(User.iin == iin))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    result = await db.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    hashed_password = get_password_hash(user_data.password)
    user = User(
        iin=user_data.iin,
        name=user_data.name,
        phone=user_data.phone,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, iin: str, password: str) -> User | None:
    user = await get_user_by_iin(db, iin)
    if not user:
        return None
    valid, new_hash = verify_and_upgrade_password(password, user.hashed_password)
    if not valid:
        return None
    if new_hash:
        # Migrated (e.g. old Django pbkdf2_sha256) or otherwise deprecated
        # hash - upgrade it to bcrypt now that we have the plaintext.
        user.hashed_password = new_hash
        await db.commit()
    return user


async def update_user_password(db: AsyncSession, user: User, new_password: str) -> User:
    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    await db.refresh(user)
    return user


async def verify_user_phone(db: AsyncSession, user: User) -> User:
    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_profile(
    db: AsyncSession, user: User, user_data: UserUpdate
) -> User:
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.phone is not None:
        user.phone = user_data.phone
        user.is_verified = False
    await db.commit()
    await db.refresh(user)
    return user
