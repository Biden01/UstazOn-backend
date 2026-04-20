"""
Аутентификация для админ-панели
Admin panel authentication
"""
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from src.core.security import create_access_token, decode_token, verify_password
from src.db.session import async_session_maker
from src.services.user_service import get_user_by_iin


class AdminAuth(AuthenticationBackend):
    """Аутентификация админ-панели через JWT"""

    async def login(self, request: Request) -> bool:
        """Обработка логина в админ-панель"""
        form = await request.form()
        iin = form.get("username")  # SQLAdmin использует "username"
        password = form.get("password")

        if not iin or not password:
            return False

        async with async_session_maker() as session:
            user = await get_user_by_iin(session, str(iin))

            if not user:
                return False

            if not verify_password(str(password), user.hashed_password):
                return False

            # Проверяем, что пользователь - админ или суперпользователь
            if not (user.is_admin or user.is_superuser):
                return False

            # Создаём токен и сохраняем в сессии
            token = create_access_token(subject=str(user.id))
            request.session.update({"admin_token": token, "user_id": user.id})

        return True

    async def logout(self, request: Request) -> bool:
        """Выход из админ-панели"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверка аутентификации для каждого запроса"""
        token = request.session.get("admin_token")

        if not token:
            return False

        # Проверяем токен
        payload = decode_token(token)
        if not payload:
            return False

        user_id = payload.get("sub")
        if not user_id:
            return False

        # Проверяем, что пользователь всё ещё админ
        async with async_session_maker() as session:
            from src.services.user_service import get_user_by_id
            user = await get_user_by_id(session, int(user_id))

            if not user or not user.is_active:
                return False

            if not (user.is_admin or user.is_superuser):
                return False

        return True
