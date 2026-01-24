"""
Настройка админ-панели
Admin panel setup
"""
from sqladmin import Admin
from fastapi import FastAPI

from src.core.config import settings
from src.db.session import engine
from .auth import AdminAuth
from .views import (
    UserAdmin,
    SubjectAdmin,
    InstitutionTypeAdmin,
    TemplateAdmin,
    WindowAdmin,
    CardTopicAdmin,
    CardAdmin,
    QMJAdmin,
    QMJFileAdmin,
    TestAdmin,
    QuestionAdmin,
    AnswerAdmin,
)


def setup_admin(app: FastAPI) -> Admin:
    """
    Настройка и регистрация админ-панели
    Setup and register admin panel
    """
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    
    admin = Admin(
        app,
        engine,
        title="UstazOn Admin",
        base_url="/admin",
        authentication_backend=authentication_backend,
    )

    # Регистрация моделей в порядке важности
    # Users
    admin.add_view(UserAdmin)

    # Educational content
    admin.add_view(SubjectAdmin)
    admin.add_view(InstitutionTypeAdmin)

    # Templates and Windows
    admin.add_view(TemplateAdmin)
    admin.add_view(WindowAdmin)

    # Cards
    admin.add_view(CardTopicAdmin)
    admin.add_view(CardAdmin)

    # QMJ (Lesson Plans)
    admin.add_view(QMJAdmin)
    admin.add_view(QMJFileAdmin)

    # Tests
    admin.add_view(TestAdmin)
    admin.add_view(QuestionAdmin)
    admin.add_view(AnswerAdmin)

    return admin
