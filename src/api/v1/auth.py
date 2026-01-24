from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, create_refresh_token, decode_token
from src.db.session import get_db
from src.schemas.user import (
    MessageResponse,
    ResetPasswordRequest,
    SendCodeRequest,
    Token,
    TokenRefresh,
    UserCreate,
    UserLogin,
    UserResponse,
    VerifyCodeRequest,
)
from src.services import sms_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем, существует ли пользователь с таким ИИН
    existing_user = await user_service.get_user_by_iin(db, user_data.iin)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким ИИН уже существует",
        )

    # Проверяем, существует ли пользователь с таким телефоном
    existing_phone = await user_service.get_user_by_phone(db, user_data.phone)
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким номером телефона уже существует",
        )

    # Создаём пользователя
    await user_service.create_user(db, user_data)

    return MessageResponse(message="Регистрация успешна. Пожалуйста, подтвердите номер телефона.")


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await user_service.authenticate_user(db, credentials.iin, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный ИИН или пароль",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = decode_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh token",
        )

    user_id = payload.get("sub")
    user = await user_service.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/send-code", response_model=MessageResponse)
async def send_verification_code(
    data: SendCodeRequest, db: AsyncSession = Depends(get_db)
):
    await sms_service.create_verification_code(db, data.phone, purpose="verify")
    return MessageResponse(message="Код отправлен на указанный номер")


@router.post("/verify-phone", response_model=MessageResponse)
async def verify_phone(data: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    is_valid = await sms_service.verify_code(db, data.phone, data.code, purpose="verify")
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истёкший код",
        )

    # Находим пользователя и верифицируем его
    user = await user_service.get_user_by_phone(db, data.phone)
    if user:
        await user_service.verify_user_phone(db, user)

    return MessageResponse(message="Номер телефона подтверждён")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: SendCodeRequest, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user_by_phone(db, data.phone)
    if not user:
        # Не раскрываем, существует ли пользователь
        return MessageResponse(message="Если аккаунт существует, код будет отправлен")

    await sms_service.create_verification_code(db, data.phone, purpose="reset_password")
    return MessageResponse(message="Код отправлен на указанный номер")


@router.post("/verify-reset-code", response_model=MessageResponse)
async def verify_reset_code(data: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    is_valid = await sms_service.check_code_valid(
        db, data.phone, data.code, purpose="reset_password"
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истёкший код",
        )

    return MessageResponse(message="Код подтверждён")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    # Проверяем и используем код
    is_valid = await sms_service.verify_code(
        db, data.phone, data.code, purpose="reset_password"
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истёкший код подтверждения",
        )

    user = await user_service.get_user_by_phone(db, data.phone)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    await user_service.update_user_password(db, user, data.new_password)

    return MessageResponse(message="Пароль успешно изменён")
