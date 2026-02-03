"""
Admin panel setup
"""
from sqladmin import Admin
from fastapi import FastAPI

from src.core.config import settings
from src.db.session import engine
from .auth import AdminAuth
from .views import (
    UserAdmin,
    SubscribeAdmin,
    SubjectAdmin,
    InstitutionTypeAdmin,
    TemplateAdmin,
    WindowAdmin,
    CardTopicAdmin,
    CardAdmin,
    QMJAdmin,
    QMJFileAdmin,
)

def setup_admin(app: FastAPI) -> Admin:
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)

    admin = Admin(
        app,
        engine,
        title="UstazOn Admin",
        base_url="/admin",
        authentication_backend=authentication_backend,
    )

    admin.add_view(UserAdmin)
    admin.add_view(SubscribeAdmin)
    admin.add_view(SubjectAdmin)
    admin.add_view(InstitutionTypeAdmin)
    admin.add_view(TemplateAdmin)
    admin.add_view(WindowAdmin)
    admin.add_view(CardTopicAdmin)
    admin.add_view(CardAdmin)
    admin.add_view(QMJAdmin)
    admin.add_view(QMJFileAdmin)

    return admin
