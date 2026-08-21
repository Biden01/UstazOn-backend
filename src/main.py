from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.admin import setup_admin
from src.api.v1.router import api_router
from src.core.config import settings
from src.core.storage import UPLOAD_DIR
from src.db.base import Base
from src.db.session import engine
from src.models import User, VerificationCode  # noqa: F401 - для создания таблиц


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём таблицы при старте (для разработки)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Админ-панель
setup_admin(app)

# Статическая раздача файлов
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
