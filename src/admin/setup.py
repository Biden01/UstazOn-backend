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
    VerificationCodeAdmin,
    SubscribeAdmin,
    PageAccessAdmin,
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
    TestResultAdmin,
    TestLinkAdmin,
    ChatConversationAdmin,
    ChatMessageAdmin,
    TeachingMaterialAdmin,
    GameCategoryAdmin,
    GameTemplateAdmin,
    GameAdmin,
    GameItemAdmin,
    GameResultAdmin,
    GameLinkAdmin,
    GameRatingAdmin,
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

    # Users
    admin.add_view(UserAdmin)
    admin.add_view(VerificationCodeAdmin)

    # Subscriptions
    admin.add_view(SubscribeAdmin)
    admin.add_view(PageAccessAdmin)

    # Content structure
    admin.add_view(SubjectAdmin)
    admin.add_view(InstitutionTypeAdmin)
    admin.add_view(TemplateAdmin)
    admin.add_view(WindowAdmin)

    # Cards
    admin.add_view(CardTopicAdmin)
    admin.add_view(CardAdmin)

    # QMJ
    admin.add_view(QMJAdmin)
    admin.add_view(QMJFileAdmin)

    # Tests
    admin.add_view(TestAdmin)
    admin.add_view(QuestionAdmin)
    admin.add_view(AnswerAdmin)
    admin.add_view(TestResultAdmin)
    admin.add_view(TestLinkAdmin)

    # AI
    admin.add_view(ChatConversationAdmin)
    admin.add_view(ChatMessageAdmin)
    admin.add_view(TeachingMaterialAdmin)

    # Games
    admin.add_view(GameCategoryAdmin)
    admin.add_view(GameTemplateAdmin)
    admin.add_view(GameAdmin)
    admin.add_view(GameItemAdmin)
    admin.add_view(GameResultAdmin)
    admin.add_view(GameLinkAdmin)
    admin.add_view(GameRatingAdmin)

    return admin
