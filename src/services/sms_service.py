import logging
import random
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.user import VerificationCode

logger = logging.getLogger(__name__)


def generate_code() -> str:
    return str(random.randint(100000, 999999))


async def send_sms_mobizon(phone: str, message: str) -> bool:
    """Отправка SMS через Mobizon API."""
    if not settings.MOBIZON_API_KEY:
        logger.error("MOBIZON_API_KEY не настроен")
        return False

    # Убираем + из номера для Mobizon
    phone_clean = phone.lstrip("+")

    params = {
        "apiKey": settings.MOBIZON_API_KEY,
        "recipient": phone_clean,
        "text": message,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.MOBIZON_API_URL}/message/sendSmsMessage",
                data=params,
                timeout=30.0,
            )
            result = response.json()

            if result.get("code") == 0:
                logger.info(f"SMS отправлен на {phone}")
                return True
            else:
                logger.error(f"Ошибка Mobizon: {result.get('message')}")
                return False
    except Exception as e:
        logger.error(f"Ошибка отправки SMS: {e}")
        return False


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

    # Отправка SMS
    if settings.SMS_ENABLED:
        message = f"UstazOn: Ваш код подтверждения: {code}"
        await send_sms_mobizon(phone, message)
    else:
        logger.info(f"[DEV] Код для {phone}: {code}")

    return verification


async def check_code_valid(
    db: AsyncSession, phone: str, code: str, purpose: str
) -> bool:
    """Проверяет код без его использования (для промежуточной валидации)."""
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
    return verification is not None


async def verify_code(
    db: AsyncSession, phone: str, code: str, purpose: str
) -> bool:
    """Проверяет и использует код (помечает как использованный)."""
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
