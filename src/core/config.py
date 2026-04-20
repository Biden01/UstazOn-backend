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

    # Redis
    REDIS_URL: str = ""

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://185.129.51.101",
        "https://ustazon.com",
        "https://www.ustazon.com"
    ]

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

    # AI (Gamma)
    GAMMA_API_KEY: str = ""

    # Unsplash
    UNSPLASH_API_KEY: str = ""

    # Media files
    MEDIA_URL: str = "http://localhost:8000/media/"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
