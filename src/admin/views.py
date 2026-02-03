"""
Admin model views
"""
from datetime import date
from sqladmin import ModelView, BaseView
from sqlalchemy import func, select

from src.models.user import User, VerificationCode
from src.models.subject import Subject, InstitutionType, Template, Window
from src.models.subscription import Subscribe, PageAccess
from src.models.card import Card, CardTopic
from src.models.test import Test, Question, Answer, TestResult, TestLink
from src.models.qmj import QMJ, QMJFile
from src.models.ai_chat import ChatConversation, ChatMessage
from src.models.teaching_materials import TeachingMaterial
from src.models.game import (
    Game, GameTemplate, GameCategory, GameItem,
    GameResult, GameLink, GameRating,
)


# ──────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────

class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"
    category = "Пользователи"

    column_list = [
        User.id, User.iin, User.name, User.phone,
        User.is_active, User.is_verified, User.is_admin, User.is_superuser,
        User.created_at,
    ]
    column_searchable_list = [User.name, User.phone, User.iin]
    column_sortable_list = [User.id, User.name, User.created_at, User.is_active]
    column_default_sort = [(User.id, True)]

    column_labels = {
        User.id: "ID",
        User.iin: "ИИН",
        User.name: "Имя",
        User.phone: "Телефон",
        User.is_active: "Активен",
        User.is_verified: "Верифицирован",
        User.is_admin: "Админ",
        User.is_superuser: "Суперпользователь",
        User.created_at: "Создан",
        User.updated_at: "Обновлён",
        User.subscriptions: "Подписки",
    }

    form_columns = [
        User.iin,
        User.name,
        User.phone,
        User.is_active,
        User.is_verified,
        User.is_admin,
        User.is_superuser,
    ]

    column_details_list = [
        User.id, User.iin, User.name, User.phone,
        User.is_active, User.is_verified, User.is_admin, User.is_superuser,
        User.created_at, User.subscriptions,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = False
    can_view_details = True
    can_export = True

    column_formatters = {
        User.subscriptions: lambda m, a: len(m.subscriptions) if m.subscriptions else 0
    }

    detail_template = "user_detail.html"


class VerificationCodeAdmin(ModelView, model=VerificationCode):
    name = "Код верификации"
    name_plural = "Коды верификации"
    icon = "fa-solid fa-shield-halved"
    category = "Пользователи"

    column_list = [
        VerificationCode.id, VerificationCode.phone, VerificationCode.purpose,
        VerificationCode.is_used, VerificationCode.expires_at, VerificationCode.created_at,
    ]
    column_searchable_list = [VerificationCode.phone]
    column_sortable_list = [VerificationCode.id, VerificationCode.created_at]
    column_default_sort = [(VerificationCode.id, True)]

    column_labels = {
        VerificationCode.id: "ID",
        VerificationCode.phone: "Телефон",
        VerificationCode.code: "Код",
        VerificationCode.purpose: "Назначение",
        VerificationCode.is_used: "Использован",
        VerificationCode.expires_at: "Истекает",
        VerificationCode.created_at: "Создан",
    }

    column_details_exclude_list = [VerificationCode.code]

    form_columns = [
        VerificationCode.phone,
        VerificationCode.purpose,
        VerificationCode.is_used,
        VerificationCode.expires_at,
    ]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True


# ──────────────────────────────────────────────
# Subscriptions
# ──────────────────────────────────────────────

class SubscribeAdmin(ModelView, model=Subscribe):
    name = "Подписка"
    name_plural = "Подписки"
    icon = "fa-solid fa-credit-card"
    category = "Подписки"

    column_list = [
        Subscribe.id,
        "user.name",
        "user.phone",
        "subject.name",
        "institution_type.name",
        Subscribe.end_date,
        Subscribe.created_at,
    ]
    column_searchable_list = [
        "user.name",
        "user.phone",
        "subject.name",
        "institution_type.name"
    ]
    column_sortable_list = [
        Subscribe.id,
        "user.name",
        "subject.name",
        Subscribe.end_date,
        Subscribe.created_at,
    ]
    column_default_sort = [(Subscribe.id, True)]

    column_labels = {
        Subscribe.id: "ID",
        "user.name": "Пользователь",
        "user.phone": "Телефон",
        "subject.name": "Предмет",
        "institution_type.name": "Тип учреждения",
        Subscribe.end_date: "Дата окончания",
        Subscribe.created_at: "Создана",
    }

    column_formatters = {
        Subscribe.end_date: lambda m, a: (
            f"✅ {m.end_date}" if m.end_date >= date.today()
            else f"❌ {m.end_date}"
        )
    }

    column_details_list = [
        Subscribe.id,
        "user.name",
        "user.phone",
        "user.iin",
        "subject.name",
        "subject.code",
        "institution_type.name",
        Subscribe.end_date,
        Subscribe.created_at,
        Subscribe.updated_at,
    ]

    form_columns = [
        Subscribe.user_id,
        Subscribe.subject_id,
        Subscribe.institution_type_id,
        Subscribe.end_date,
    ]

    detail_template = "admin/subscribe_detail.html"

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class PageAccessAdmin(ModelView, model=PageAccess):
    name = "Доступ к странице"
    name_plural = "Доступ к страницам"
    icon = "fa-solid fa-lock"
    category = "Подписки"

    column_list = [
        PageAccess.id, PageAccess.name, PageAccess.url_pattern,
        PageAccess.protection_level, PageAccess.is_active,
    ]
    column_searchable_list = [PageAccess.name, PageAccess.url_pattern]
    column_sortable_list = [PageAccess.id, PageAccess.name, PageAccess.protection_level]

    column_labels = {
        PageAccess.id: "ID",
        PageAccess.name: "Название",
        PageAccess.url_pattern: "URL паттерн",
        PageAccess.protection_level: "Уровень защиты",
        PageAccess.is_active: "Активен",
        PageAccess.description: "Описание",
    }

    form_columns = [
        PageAccess.name,
        PageAccess.url_pattern,
        PageAccess.description,
        PageAccess.protection_level,
        PageAccess.requires_specific_subject,
        PageAccess.subject_id,
        PageAccess.institution_type_id,
        PageAccess.is_active,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


# ──────────────────────────────────────────────
# Subjects / Institution Types / Templates / Windows
# ──────────────────────────────────────────────

class SubjectAdmin(ModelView, model=Subject):
    name = "Предмет"
    name_plural = "Предметы"
    icon = "fa-solid fa-book"
    category = "Контент"

    column_list = [
        Subject.id, Subject.name, Subject.code,
        Subject.image_url, Subject.created_at,
    ]
    column_searchable_list = [Subject.name, Subject.code]
    column_sortable_list = [Subject.id, Subject.name, Subject.code]
    column_default_sort = [(Subject.name, False)]

    column_labels = {
        Subject.id: "ID",
        Subject.name: "Название",
        Subject.code: "Код",
        Subject.image_url: "Изображение",
        Subject.hero_image_url: "Hero изображение",
        Subject.created_at: "Создан",
        Subject.updated_at: "Обновлён",
        Subject.institution_types: "Типы учреждений",
        Subject.windows: "Окна",
    }

    form_columns = [
        Subject.name,
        Subject.code,
        Subject.image_url,
        Subject.hero_image_url,
        Subject.institution_types,
        Subject.windows,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


class InstitutionTypeAdmin(ModelView, model=InstitutionType):
    name = "Тип учреждения"
    name_plural = "Типы учреждений"
    icon = "fa-solid fa-building"
    category = "Контент"

    column_list = [
        InstitutionType.id, InstitutionType.name, InstitutionType.code,
        InstitutionType.created_at,
    ]
    column_searchable_list = [InstitutionType.name, InstitutionType.code]
    column_sortable_list = [InstitutionType.id, InstitutionType.name]

    column_labels = {
        InstitutionType.id: "ID",
        InstitutionType.name: "Название",
        InstitutionType.code: "Код",
        InstitutionType.created_at: "Создан",
    }

    form_columns = [InstitutionType.name, InstitutionType.code]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class TemplateAdmin(ModelView, model=Template):
    name = "Шаблон"
    name_plural = "Шаблоны"
    icon = "fa-solid fa-file-alt"
    category = "Контент"

    column_list = [
        Template.id, Template.name, Template.code_name, Template.created_at,
    ]
    column_searchable_list = [Template.name, Template.code_name]
    column_sortable_list = [Template.id, Template.name]

    column_labels = {
        Template.id: "ID",
        Template.name: "Название",
        Template.code_name: "Кодовое имя",
        Template.created_at: "Создан",
    }

    form_columns = [Template.name, Template.code_name]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class WindowAdmin(ModelView, model=Window):
    name = "Окно"
    name_plural = "Окна"
    icon = "fa-solid fa-window-maximize"
    category = "Контент"

    column_list = [
        Window.id, Window.name, Window.template_id,
        Window.nsub, Window.created_at,
    ]
    column_searchable_list = [Window.name]
    column_sortable_list = [Window.id, Window.name]

    column_labels = {
        Window.id: "ID",
        Window.name: "Название",
        Window.template_id: "Шаблон",
        Window.nsub: "Требует подписку",
        Window.link: "Ссылка",
        Window.image_url: "Изображение",
        Window.created_at: "Создан",
    }

    form_columns = [
        Window.name,
        Window.template_id,
        Window.nsub,
        Window.link,
        Window.image_url,
        Window.subjects,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


# ──────────────────────────────────────────────
# Cards
# ──────────────────────────────────────────────

class CardTopicAdmin(ModelView, model=CardTopic):
    name = "Тема карточки"
    name_plural = "Темы карточек"
    icon = "fa-solid fa-tags"
    category = "Карточки"

    column_list = [
        CardTopic.id, CardTopic.topic,
        CardTopic.parent_topic_id, CardTopic.created_at,
    ]
    column_searchable_list = [CardTopic.topic]
    column_sortable_list = [CardTopic.id, CardTopic.topic]

    column_labels = {
        CardTopic.id: "ID",
        CardTopic.topic: "Тема",
        CardTopic.parent_topic_id: "Родительская тема",
        CardTopic.created_at: "Создан",
    }

    form_columns = [
        CardTopic.topic,
        CardTopic.parent_topic_id,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class CardAdmin(ModelView, model=Card):
    name = "Карточка"
    name_plural = "Карточки"
    icon = "fa-solid fa-id-card"
    category = "Карточки"

    column_list = [
        Card.id, Card.name, Card.grade, Card.quarter,
        Card.subject_card, Card.topic_id, Card.window_id,
        Card.author_id, Card.created_at,
    ]
    column_searchable_list = [Card.name, Card.subject_card, Card.description]
    column_sortable_list = [
        Card.id, Card.name, Card.grade, Card.quarter, Card.created_at,
    ]
    column_default_sort = [(Card.id, True)]

    column_labels = {
        Card.id: "ID",
        Card.name: "Название",
        Card.description: "Описание",
        Card.grade: "Класс",
        Card.quarter: "Четверть",
        Card.subject_card: "Предмет (код)",
        Card.topic_id: "Тема",
        Card.window_id: "Окно",
        Card.author_id: "Автор",
        Card.file_path: "Файл",
        Card.url: "URL",
        Card.iframe: "Iframe",
        Card.created_at: "Создан",
    }

    form_columns = [
        Card.name,
        Card.description,
        Card.grade,
        Card.quarter,
        Card.subject_card,
        Card.file_path,
        Card.url,
        Card.iframe,
        Card.img1_url,
        Card.img2_url,
        Card.img3_url,
        Card.img4_url,
        Card.img5_url,
        Card.video1_url,
        Card.video1_file_path,
        Card.topic_id,
        Card.window_id,
        Card.author_id,
        Card.subjects,
        Card.institution_types,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestAdmin(ModelView, model=Test):
    name = "Тест"
    name_plural = "Тесты"
    icon = "fa-solid fa-clipboard-check"
    category = "Тесты"

    column_list = [
        Test.id, Test.title, Test.subject, Test.difficulty,
        Test.duration, Test.user_id, Test.created_at,
    ]
    column_searchable_list = [Test.title, Test.subject]
    column_sortable_list = [
        Test.id, Test.title, Test.difficulty, Test.duration, Test.created_at,
    ]
    column_default_sort = [(Test.id, True)]

    column_labels = {
        Test.id: "ID",
        Test.title: "Название",
        Test.subject: "Предмет",
        Test.difficulty: "Сложность",
        Test.duration: "Длительность (мин)",
        Test.user_id: "Автор",
        Test.created_at: "Создан",
        Test.updated_at: "Обновлён",
    }

    form_columns = [
        Test.title,
        Test.subject,
        Test.difficulty,
        Test.duration,
        Test.user_id,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


class QuestionAdmin(ModelView, model=Question):
    name = "Вопрос"
    name_plural = "Вопросы"
    icon = "fa-solid fa-question-circle"
    category = "Тесты"

    column_list = [
        Question.id, Question.text, Question.test_id,
        Question.order, Question.created_at,
    ]
    column_searchable_list = [Question.text]
    column_sortable_list = [Question.id, Question.test_id, Question.order]

    column_labels = {
        Question.id: "ID",
        Question.text: "Текст",
        Question.test_id: "Тест",
        Question.order: "Порядок",
        Question.photo: "Фото",
        Question.video: "Видео",
        Question.created_at: "Создан",
    }

    form_columns = [
        Question.test_id,
        Question.text,
        Question.photo,
        Question.video,
        Question.order,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class AnswerAdmin(ModelView, model=Answer):
    name = "Ответ"
    name_plural = "Ответы"
    icon = "fa-solid fa-check-circle"
    category = "Тесты"

    column_list = [
        Answer.id, Answer.text, Answer.is_correct,
        Answer.question_id, Answer.order,
    ]
    column_searchable_list = [Answer.text]
    column_sortable_list = [Answer.id, Answer.question_id, Answer.order]

    column_labels = {
        Answer.id: "ID",
        Answer.text: "Текст",
        Answer.is_correct: "Правильный",
        Answer.question_id: "Вопрос",
        Answer.order: "Порядок",
        Answer.created_at: "Создан",
    }

    form_columns = [
        Answer.question_id,
        Answer.text,
        Answer.is_correct,
        Answer.order,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class TestResultAdmin(ModelView, model=TestResult):
    name = "Результат теста"
    name_plural = "Результаты тестов"
    icon = "fa-solid fa-chart-bar"
    category = "Тесты"

    column_list = [
        TestResult.id, TestResult.test_id, TestResult.student_name,
        TestResult.group_name, TestResult.correct_answers,
        TestResult.total_questions, TestResult.percentage,
        TestResult.warning_count, TestResult.completed_at,
    ]
    column_searchable_list = [TestResult.student_name, TestResult.group_name]
    column_sortable_list = [
        TestResult.id, TestResult.percentage, TestResult.completed_at,
    ]
    column_default_sort = [(TestResult.id, True)]

    column_labels = {
        TestResult.id: "ID",
        TestResult.test_id: "Тест",
        TestResult.student_name: "Студент",
        TestResult.group_name: "Группа",
        TestResult.correct_answers: "Правильных",
        TestResult.total_questions: "Всего вопросов",
        TestResult.percentage: "Процент",
        TestResult.warning_count: "Предупреждения",
        TestResult.attempt_count: "Попытка",
        TestResult.completed_at: "Завершён",
    }

    form_columns = [
        TestResult.test_id,
        TestResult.student_name,
        TestResult.group_name,
        TestResult.correct_answers,
        TestResult.total_questions,
        TestResult.percentage,
        TestResult.warning_count,
        TestResult.attempt_count,
    ]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


class TestLinkAdmin(ModelView, model=TestLink):
    name = "Ссылка теста"
    name_plural = "Ссылки тестов"
    icon = "fa-solid fa-link"
    category = "Тесты"

    column_list = [
        TestLink.id, TestLink.test_id, TestLink.group_name,
        TestLink.is_active, TestLink.attempts_count,
        TestLink.max_attempts, TestLink.expires_at, TestLink.created_at,
    ]
    column_searchable_list = [TestLink.group_name, TestLink.unique_hash]
    column_sortable_list = [TestLink.id, TestLink.created_at]
    column_default_sort = [(TestLink.id, True)]

    column_labels = {
        TestLink.id: "ID",
        TestLink.test_id: "Тест",
        TestLink.unique_hash: "Хеш",
        TestLink.group_name: "Группа",
        TestLink.is_active: "Активна",
        TestLink.max_attempts: "Макс. попыток",
        TestLink.attempts_count: "Использовано",
        TestLink.expires_at: "Истекает",
        TestLink.created_at: "Создана",
    }

    form_columns = [
        TestLink.test_id,
        TestLink.unique_hash,
        TestLink.group_name,
        TestLink.is_active,
        TestLink.max_attempts,
        TestLink.expires_at,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


# ──────────────────────────────────────────────
# QMJ (Lesson Plans)
# ──────────────────────────────────────────────

class QMJAdmin(ModelView, model=QMJ):
    name = "ҚМЖ"
    name_plural = "ҚМЖ"
    icon = "fa-solid fa-calendar-alt"
    category = "ҚМЖ"

    column_list = [
        QMJ.id, QMJ.title, QMJ.grade, QMJ.quarter,
        QMJ.code, QMJ.hour, QMJ.order,
        QMJ.author_id, QMJ.created_at,
    ]
    column_searchable_list = [QMJ.title, QMJ.code, QMJ.text]
    column_sortable_list = [
        QMJ.id, QMJ.grade, QMJ.quarter, QMJ.order, QMJ.created_at,
    ]
    column_default_sort = [(QMJ.order, False), (QMJ.id, True)]

    column_labels = {
        QMJ.id: "ID",
        QMJ.title: "Название",
        QMJ.grade: "Класс",
        QMJ.quarter: "Четверть",
        QMJ.code: "Код предмета",
        QMJ.text: "Текст",
        QMJ.hour: "Часы",
        QMJ.order: "Порядок",
        QMJ.file: "Файл",
        QMJ.author_id: "Автор",
        QMJ.created_at: "Создан",
    }

    form_columns = [
        QMJ.grade,
        QMJ.quarter,
        QMJ.code,
        QMJ.title,
        QMJ.text,
        QMJ.hour,
        QMJ.order,
        QMJ.file,
        QMJ.author_id,
        QMJ.subjects,
        QMJ.institution_types,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


class QMJFileAdmin(ModelView, model=QMJFile):
    name = "Файл ҚМЖ"
    name_plural = "Файлы ҚМЖ"
    icon = "fa-solid fa-file"
    category = "ҚМЖ"

    column_list = [
        QMJFile.id, QMJFile.file, QMJFile.file_type,
        QMJFile.file_size, QMJFile.qmj_id, QMJFile.uploaded_at,
    ]
    column_searchable_list = [QMJFile.file]
    column_sortable_list = [QMJFile.id, QMJFile.uploaded_at]

    column_labels = {
        QMJFile.id: "ID",
        QMJFile.file: "Путь",
        QMJFile.file_type: "Тип",
        QMJFile.file_size: "Размер",
        QMJFile.qmj_id: "ҚМЖ",
        QMJFile.uploaded_by_id: "Загрузил",
        QMJFile.uploaded_at: "Загружен",
    }

    form_columns = [
        QMJFile.qmj_id,
        QMJFile.file,
        QMJFile.file_type,
        QMJFile.file_size,
        QMJFile.uploaded_by_id,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


# ──────────────────────────────────────────────
# AI Chat
# ──────────────────────────────────────────────

class ChatConversationAdmin(ModelView, model=ChatConversation):
    name = "Диалог"
    name_plural = "Диалоги AI"
    icon = "fa-solid fa-comments"
    category = "AI"

    column_list = [
        ChatConversation.id, ChatConversation.user_id,
        ChatConversation.title, ChatConversation.subject,
        ChatConversation.message_count, ChatConversation.total_tokens,
        ChatConversation.created_at,
    ]
    column_searchable_list = [ChatConversation.title, ChatConversation.subject]
    column_sortable_list = [
        ChatConversation.id, ChatConversation.message_count,
        ChatConversation.total_tokens, ChatConversation.created_at,
    ]
    column_default_sort = [(ChatConversation.id, True)]

    column_labels = {
        ChatConversation.id: "ID",
        ChatConversation.user_id: "Пользователь",
        ChatConversation.title: "Тема",
        ChatConversation.subject: "Предмет",
        ChatConversation.message_count: "Сообщений",
        ChatConversation.total_tokens: "Токенов",
        ChatConversation.created_at: "Создан",
    }

    form_columns = [
        ChatConversation.user_id,
        ChatConversation.title,
        ChatConversation.subject,
    ]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


class ChatMessageAdmin(ModelView, model=ChatMessage):
    name = "Сообщение AI"
    name_plural = "Сообщения AI"
    icon = "fa-solid fa-message"
    category = "AI"

    column_list = [
        ChatMessage.id, ChatMessage.conversation_id,
        ChatMessage.role, ChatMessage.total_tokens,
        ChatMessage.created_at,
    ]
    column_searchable_list = [ChatMessage.content]
    column_sortable_list = [ChatMessage.id, ChatMessage.created_at]
    column_default_sort = [(ChatMessage.id, True)]

    column_labels = {
        ChatMessage.id: "ID",
        ChatMessage.conversation_id: "Диалог",
        ChatMessage.role: "Роль",
        ChatMessage.content: "Содержимое",
        ChatMessage.input_tokens: "Входных токенов",
        ChatMessage.output_tokens: "Выходных токенов",
        ChatMessage.total_tokens: "Всего токенов",
        ChatMessage.created_at: "Создан",
    }

    form_columns = [
        ChatMessage.conversation_id,
        ChatMessage.role,
        ChatMessage.content,
    ]

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


# ──────────────────────────────────────────────
# Teaching Materials
# ──────────────────────────────────────────────

class TeachingMaterialAdmin(ModelView, model=TeachingMaterial):
    name = "Учебный материал"
    name_plural = "Учебные материалы"
    icon = "fa-solid fa-graduation-cap"
    category = "AI"

    column_list = [
        TeachingMaterial.id, TeachingMaterial.title,
        TeachingMaterial.material_type, TeachingMaterial.subject,
        TeachingMaterial.grade, TeachingMaterial.user_id,
        TeachingMaterial.ai_model, TeachingMaterial.view_count,
        TeachingMaterial.download_count, TeachingMaterial.created_at,
    ]
    column_searchable_list = [
        TeachingMaterial.title, TeachingMaterial.subject, TeachingMaterial.topic,
    ]
    column_sortable_list = [
        TeachingMaterial.id, TeachingMaterial.material_type,
        TeachingMaterial.created_at, TeachingMaterial.view_count,
    ]
    column_default_sort = [(TeachingMaterial.id, True)]

    column_labels = {
        TeachingMaterial.id: "ID",
        TeachingMaterial.title: "Название",
        TeachingMaterial.material_type: "Тип",
        TeachingMaterial.subject: "Предмет",
        TeachingMaterial.grade: "Класс",
        TeachingMaterial.topic: "Тема",
        TeachingMaterial.user_id: "Пользователь",
        TeachingMaterial.ai_model: "AI модель",
        TeachingMaterial.difficulty_level: "Сложность",
        TeachingMaterial.view_count: "Просмотров",
        TeachingMaterial.download_count: "Скачиваний",
        TeachingMaterial.created_at: "Создан",
    }

    form_columns = [
        TeachingMaterial.user_id,
        TeachingMaterial.material_type,
        TeachingMaterial.title,
        TeachingMaterial.subject,
        TeachingMaterial.grade,
        TeachingMaterial.topic,
        TeachingMaterial.file_path,
        TeachingMaterial.ai_model,
        TeachingMaterial.difficulty_level,
        TeachingMaterial.estimated_time,
        TeachingMaterial.question_count,
    ]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


# ──────────────────────────────────────────────
# Games
# ──────────────────────────────────────────────

class GameCategoryAdmin(ModelView, model=GameCategory):
    name = "Категория игр"
    name_plural = "Категории игр"
    icon = "fa-solid fa-layer-group"
    category = "Игры"

    column_list = [
        GameCategory.id, GameCategory.name, GameCategory.icon,
        GameCategory.color, GameCategory.is_active, GameCategory.order,
    ]
    column_searchable_list = [GameCategory.name]
    column_sortable_list = [GameCategory.id, GameCategory.name, GameCategory.order]

    column_labels = {
        GameCategory.id: "ID",
        GameCategory.name: "Название",
        GameCategory.description: "Описание",
        GameCategory.icon: "Иконка",
        GameCategory.color: "Цвет",
        GameCategory.is_active: "Активна",
        GameCategory.order: "Порядок",
    }

    form_columns = [
        GameCategory.name,
        GameCategory.description,
        GameCategory.icon,
        GameCategory.color,
        GameCategory.is_active,
        GameCategory.order,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class GameTemplateAdmin(ModelView, model=GameTemplate):
    name = "Шаблон игры"
    name_plural = "Шаблоны игр"
    icon = "fa-solid fa-puzzle-piece"
    category = "Игры"

    column_list = [
        GameTemplate.id, GameTemplate.name, GameTemplate.game_type,
        GameTemplate.is_active, GameTemplate.is_premium, GameTemplate.order,
    ]
    column_searchable_list = [GameTemplate.name, GameTemplate.game_type]
    column_sortable_list = [
        GameTemplate.id, GameTemplate.name, GameTemplate.order,
    ]

    column_labels = {
        GameTemplate.id: "ID",
        GameTemplate.name: "Название",
        GameTemplate.game_type: "Тип",
        GameTemplate.description: "Описание",
        GameTemplate.instruction: "Инструкция",
        GameTemplate.is_active: "Активен",
        GameTemplate.is_premium: "Премиум",
        GameTemplate.order: "Порядок",
        GameTemplate.min_items: "Мин. элементов",
        GameTemplate.max_items: "Макс. элементов",
    }

    form_columns = [
        GameTemplate.name,
        GameTemplate.game_type,
        GameTemplate.description,
        GameTemplate.instruction,
        GameTemplate.preview_image,
        GameTemplate.icon,
        GameTemplate.min_items,
        GameTemplate.max_items,
        GameTemplate.is_active,
        GameTemplate.is_premium,
        GameTemplate.order,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class GameAdmin(ModelView, model=Game):
    name = "Игра"
    name_plural = "Игры"
    icon = "fa-solid fa-gamepad"
    category = "Игры"

    column_list = [
        Game.id, Game.title, Game.difficulty,
        Game.grade, Game.quarter,
        Game.is_public, Game.is_featured,
        Game.views_count, Game.plays_count,
        Game.template_id, Game.author_id, Game.created_at,
    ]
    column_searchable_list = [Game.title, Game.description]
    column_sortable_list = [
        Game.id, Game.title, Game.grade,
        Game.views_count, Game.plays_count, Game.created_at,
    ]
    column_default_sort = [(Game.id, True)]

    column_labels = {
        Game.id: "ID",
        Game.title: "Название",
        Game.description: "Описание",
        Game.difficulty: "Сложность",
        Game.grade: "Класс",
        Game.quarter: "Четверть",
        Game.is_public: "Публичная",
        Game.is_featured: "Рекомендуемая",
        Game.views_count: "Просмотры",
        Game.plays_count: "Игры",
        Game.likes_count: "Лайки",
        Game.template_id: "Шаблон",
        Game.author_id: "Автор",
        Game.created_at: "Создана",
    }

    form_columns = [
        Game.title,
        Game.description,
        Game.difficulty,
        Game.grade,
        Game.quarter,
        Game.time_limit,
        Game.attempts_limit,
        Game.show_correct_answers,
        Game.shuffle_items,
        Game.is_public,
        Game.is_featured,
        Game.allow_embedding,
        Game.template_id,
        Game.author_id,
        Game.topic_id,
        Game.subjects,
        Game.institution_types,
        Game.categories,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


class GameItemAdmin(ModelView, model=GameItem):
    name = "Элемент игры"
    name_plural = "Элементы игр"
    icon = "fa-solid fa-cube"
    category = "Игры"

    column_list = [
        GameItem.id, GameItem.game_id, GameItem.item_type,
        GameItem.question, GameItem.answer,
        GameItem.points, GameItem.order, GameItem.is_active,
    ]
    column_searchable_list = [GameItem.question, GameItem.answer]
    column_sortable_list = [GameItem.id, GameItem.game_id, GameItem.order]

    column_labels = {
        GameItem.id: "ID",
        GameItem.game_id: "Игра",
        GameItem.item_type: "Тип",
        GameItem.question: "Вопрос",
        GameItem.answer: "Ответ",
        GameItem.points: "Очки",
        GameItem.order: "Порядок",
        GameItem.is_active: "Активен",
    }

    form_columns = [
        GameItem.game_id,
        GameItem.item_type,
        GameItem.question,
        GameItem.answer,
        GameItem.hint,
        GameItem.explanation,
        GameItem.image,
        GameItem.audio,
        GameItem.video,
        GameItem.video_url,
        GameItem.points,
        GameItem.time_limit,
        GameItem.order,
        GameItem.is_active,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class GameResultAdmin(ModelView, model=GameResult):
    name = "Результат игры"
    name_plural = "Результаты игр"
    icon = "fa-solid fa-trophy"
    category = "Игры"

    column_list = [
        GameResult.id, GameResult.game_id, GameResult.player_name,
        GameResult.score, GameResult.max_score, GameResult.percentage,
        GameResult.time_spent, GameResult.completed_at,
    ]
    column_searchable_list = [GameResult.player_name, GameResult.group_name]
    column_sortable_list = [
        GameResult.id, GameResult.score, GameResult.percentage,
        GameResult.completed_at,
    ]
    column_default_sort = [(GameResult.id, True)]

    column_labels = {
        GameResult.id: "ID",
        GameResult.game_id: "Игра",
        GameResult.player_name: "Игрок",
        GameResult.player_email: "Email",
        GameResult.group_name: "Группа",
        GameResult.score: "Очки",
        GameResult.max_score: "Макс. очков",
        GameResult.percentage: "Процент",
        GameResult.correct_answers: "Правильных",
        GameResult.total_questions: "Всего вопросов",
        GameResult.time_spent: "Время (сек)",
        GameResult.completed_at: "Завершён",
    }

    form_columns = [
        GameResult.game_id,
        GameResult.player_name,
        GameResult.group_name,
        GameResult.score,
        GameResult.max_score,
        GameResult.percentage,
        GameResult.correct_answers,
        GameResult.total_questions,
        GameResult.time_spent,
    ]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True


class GameLinkAdmin(ModelView, model=GameLink):
    name = "Ссылка игры"
    name_plural = "Ссылки игр"
    icon = "fa-solid fa-share-nodes"
    category = "Игры"

    column_list = [
        GameLink.id, GameLink.game_id, GameLink.group_name,
        GameLink.is_active, GameLink.attempts_count,
        GameLink.max_attempts, GameLink.expires_at, GameLink.created_at,
    ]
    column_searchable_list = [GameLink.group_name, GameLink.unique_hash]
    column_sortable_list = [GameLink.id, GameLink.created_at]
    column_default_sort = [(GameLink.id, True)]

    column_labels = {
        GameLink.id: "ID",
        GameLink.game_id: "Игра",
        GameLink.unique_hash: "Хеш",
        GameLink.group_name: "Группа",
        GameLink.is_active: "Активна",
        GameLink.max_attempts: "Макс. попыток",
        GameLink.attempts_count: "Использовано",
        GameLink.expires_at: "Истекает",
        GameLink.created_at: "Создана",
    }

    form_columns = [
        GameLink.game_id,
        GameLink.unique_hash,
        GameLink.group_name,
        GameLink.is_active,
        GameLink.max_attempts,
        GameLink.expires_at,
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class GameRatingAdmin(ModelView, model=GameRating):
    name = "Рейтинг игры"
    name_plural = "Рейтинги игр"
    icon = "fa-solid fa-star"
    category = "Игры"

    column_list = [
        GameRating.id, GameRating.game_id, GameRating.user_id,
        GameRating.rating, GameRating.created_at,
    ]
    column_sortable_list = [
        GameRating.id, GameRating.rating, GameRating.created_at,
    ]
    column_default_sort = [(GameRating.id, True)]

    column_labels = {
        GameRating.id: "ID",
        GameRating.game_id: "Игра",
        GameRating.user_id: "Пользователь",
        GameRating.rating: "Оценка",
        GameRating.comment: "Комментарий",
        GameRating.created_at: "Создан",
    }

    form_columns = [
        GameRating.game_id,
        GameRating.user_id,
        GameRating.rating,
        GameRating.comment,
    ]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
