from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from src.core.config import settings

# django_pbkdf2_sha256 accepts password hashes migrated from the old Django
# app (AuthPage_user.password) so those accounts can still log in; it's
# marked deprecated so verify_and_update() flags them to be upgraded to
# bcrypt the moment the user successfully logs in once.
pwd_context = CryptContext(
    schemes=["bcrypt", "django_pbkdf2_sha256"],
    deprecated=["django_pbkdf2_sha256"],
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        # Unrecognized/corrupt hash format - never crash auth over it.
        return False


def verify_and_upgrade_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Verify a password and, if it was stored with a deprecated scheme
    (e.g. a migrated Django pbkdf2_sha256 hash), return a fresh bcrypt hash
    to persist. Returns (is_valid, new_hash_or_None)."""
    if not hashed_password:
        return False, None
    try:
        valid, new_hash = pwd_context.verify_and_update(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False, None
    return bool(valid), new_hash


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.JWTError:
        return None
