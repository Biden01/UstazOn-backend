"""
Admin panel JWT authentication backend
"""
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.core.security import create_access_token, decode_token, verify_password
from src.db.session import async_session_maker
from src.services.user_service import get_user_by_iin


class AdminAuth(AuthenticationBackend):

    async def login(self, request: Request) -> bool:
        form = await request.form()
        iin = form.get("username")
        password = form.get("password")

        if not iin or not password:
            return False

        async with async_session_maker() as session:
            user = await get_user_by_iin(session, str(iin))

            if not user:
                return False

            if not verify_password(str(password), user.hashed_password):
                return False

            if not (user.is_admin or user.is_superuser):
                return False

            if not user.is_active:
                return False

            token = create_access_token(subject=str(user.id))
            request.session.update({"admin_token": token, "user_id": user.id})

        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("admin_token")

        if not token:
            return False

        payload = decode_token(token)
        if not payload:
            request.session.clear()
            return False

        user_id = payload.get("sub")
        if not user_id:
            return False

        async with async_session_maker() as session:
            from src.services.user_service import get_user_by_id
            user = await get_user_by_id(session, int(user_id))

            if not user or not user.is_active:
                request.session.clear()
                return False

            if not (user.is_admin or user.is_superuser):
                request.session.clear()
                return False

        return True
