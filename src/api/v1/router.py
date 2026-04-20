from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.users import router as users_router
from src.api.v1.subjects import router as subjects_router
from src.api.v1.cards import router as cards_router
from src.api.v1.uploads import router as uploads_router
from src.api.v1.tests import router as tests_router
from src.api.v1.qmj import router as qmj_router
from src.api.v1.ai import router as ai_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(subjects_router)
api_router.include_router(cards_router, prefix="/cards", tags=["cards"])
api_router.include_router(uploads_router, prefix="/uploads", tags=["uploads"])
api_router.include_router(tests_router, prefix="/tests", tags=["tests"])
api_router.include_router(qmj_router, prefix="/qmj", tags=["qmj"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
