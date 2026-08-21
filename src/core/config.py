import json

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "UstazOn API"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ustazon"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Get synchronous database URL for Alembic migrations"""
        return self.DATABASE_URL.replace("+asyncpg", "")

    # JWT
    # No insecure default on purpose: a guessable SECRET_KEY lets anyone forge
    # valid access tokens for any user (including admins). Set it via .env.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    # Production origins belong in .env, not hardcoded in source.
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000", "http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # SMS (Mobizon)
    SMS_ENABLED: bool = False
    MOBIZON_API_KEY: str = ""
    MOBIZON_API_URL: str = "https://api.mobizon.kz/service"

    # AI (Google Gemini)
    GOOGLE_AI_KEY: str = ""

    # AI (OpenAI)
    OPENAI_API_KEY: str = ""
    
    # AI (Anthropic)
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
