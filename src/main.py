from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.admin import setup_admin
from src.api.v1.router import api_router
from src.core.config import settings
from src.core.storage import UPLOAD_DIR
from src.db.base import Base
from src.db.session import engine
from src.models import User, VerificationCode  # noqa: F401 - для создания таблиц

templates = Jinja2Templates(directory="templates")


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

# Proxy headers (nginx → HTTPS)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Роуты
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Админ-панель
setup_admin(app)

# Custom routes
@app.get("/admin/manage-subscriptions", include_in_schema=False)
async def subscription_management_page(request: Request):
    """Render subscription management page"""
    return templates.TemplateResponse("admin/user_subscription_list.html", {"request": request})

# Статическая раздача файлов
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/media", StaticFiles(directory="media"), name="media")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
