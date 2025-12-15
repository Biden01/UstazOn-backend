import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.user import VerificationCode


def generate_code() -> str:
    return str(random.randint(100000, 999999))


async def create_verification_code(
    db: AsyncSession, phone: str, purpose: str
) -> VerificationCode:
    code = generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    verification = VerificationCode(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    # Заглушка для SMS - просто логируем код
    if not settings.SMS_ENABLED:
        print(f"[DEV SMS] Код для {phone}: {code}")

    return verification


async def verify_code(
    db: AsyncSession, phone: str, code: str, purpose: str
) -> bool:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(VerificationCode).where(
            and_(
                VerificationCode.phone == phone,
                VerificationCode.code == code,
                VerificationCode.purpose == purpose,
                VerificationCode.is_used == False,  # noqa: E712
                VerificationCode.expires_at > now,
            )
        )
    )
    verification = result.scalar_one_or_none()

    if verification:
        verification.is_used = True
        await db.commit()
        return True

    return False
