import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class UserBase(BaseModel):
    iin: str
    name: str
    phone: str


class UserCreate(UserBase):
    password: str
    confirm_password: str

    @field_validator("iin")
    @classmethod
    def validate_iin(cls, v: str) -> str:
        if not re.match(r"^\d{12}$", v):
            raise ValueError("ИИН должен содержать 12 цифр")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[а-яА-ЯёЁa-zA-Z\s\-]{2,50}$", v):
            raise ValueError("Имя должно содержать от 2 до 50 символов")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", v)
        if not re.match(r"^\+?7\d{10}$", cleaned):
            raise ValueError("Неверный формат телефона")
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r"[a-z]", v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r"\d", v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Пароли не совпадают")
        return v


class UserResponse(BaseModel):
    id: int
    iin: str
    name: str
    phone: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    iin: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class SendCodeRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", v)
        if not re.match(r"^\+?7\d{10}$", cleaned):
            raise ValueError("Неверный формат телефона")
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str


class ResetPasswordRequest(BaseModel):
    phone: str
    code: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r"[a-z]", v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r"\d", v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Пароли не совпадают")
        return v


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[а-яА-ЯёЁa-zA-Z\s\-]{2,50}$", v):
            raise ValueError("Имя должно содержать от 2 до 50 символов")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = re.sub(r"[^\d+]", "", v)
            if not re.match(r"^\+?7\d{10}$", cleaned):
                raise ValueError("Неверный формат телефона")
            if not cleaned.startswith("+"):
                cleaned = "+" + cleaned
            return cleaned
        return v


class MessageResponse(BaseModel):
    message: str
    code: str
