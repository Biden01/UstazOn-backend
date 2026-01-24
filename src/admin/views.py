"""
Административные представления для моделей
Admin views for database models
"""
from sqladmin import ModelView

from src.models import (
    User,
    Subject,
    InstitutionType,
    Template,
    Window,
    Card,
    CardTopic,
    QMJ,
    QMJFile,
    Test,
    Question,
    Answer,
)


# Увеличиваем лимит полей в WTForms
import wtforms
wtforms.validators.MAX_LENGTH = 10000


class UserAdmin(ModelView, model=User):
    """Админ-панель для пользователей"""

    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"

    column_list = [User.id, User.name, User.phone, User.is_active, User.is_verified, User.is_admin, User.is_superuser, User.created_at]
    column_searchable_list = [User.name, User.phone, User.iin]
    column_sortable_list = [User.id, User.name, User.created_at]
    column_default_sort = [(User.id, True)]

    # Ограничиваем колонки в формах
    form_columns = [
        User.iin,
        User.name,
        User.phone,
        User.hashed_password,
        User.is_active,
        User.is_verified,
        User.is_admin,
        User.is_superuser,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = False  # Не удаляем пользователей
    can_view_details = True


class SubjectAdmin(ModelView, model=Subject):
    """Админ-панель для предметов"""

    name = "Предмет"
    name_plural = "Предметы"
    icon = "fa-solid fa-book"

    column_list = [Subject.id, Subject.name, Subject.code, Subject.created_at]
    column_searchable_list = [Subject.name, Subject.code]
    column_sortable_list = [Subject.id, Subject.name]

    # Ограничиваем колонки в формах
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


class InstitutionTypeAdmin(ModelView, model=InstitutionType):
    """Админ-панель для типов учреждений"""

    name = "Тип учреждения"
    name_plural = "Типы учреждений"
    icon = "fa-solid fa-building"

    column_list = [InstitutionType.id, InstitutionType.name, InstitutionType.code, InstitutionType.created_at]
    column_searchable_list = [InstitutionType.name, InstitutionType.code]

    form_columns = [InstitutionType.name, InstitutionType.code]

    can_create = True
    can_edit = True
    can_delete = True


class TemplateAdmin(ModelView, model=Template):
    """Админ-панель для шаблонов"""

    name = "Шаблон"
    name_plural = "Шаблоны"
    icon = "fa-solid fa-file-alt"

    column_list = [Template.id, Template.name, Template.code_name, Template.created_at]
    column_searchable_list = [Template.name, Template.code_name]

    form_columns = [Template.name, Template.code_name]

    can_create = True
    can_edit = True
    can_delete = True


class WindowAdmin(ModelView, model=Window):
    """Админ-панель для окон"""

    name = "Окно"
    name_plural = "Окна"
    icon = "fa-solid fa-window-maximize"

    column_list = [Window.id, Window.name, Window.template_id, Window.nsub, Window.created_at]
    column_searchable_list = [Window.name]
    column_sortable_list = [Window.id, Window.name]

    form_columns = [
        Window.name,
        Window.template_id,
        Window.nsub,
        Window.image_url,
        Window.link,
    ]

    can_create = True
    can_edit = True
    can_delete = True


class CardTopicAdmin(ModelView, model=CardTopic):
    """Админ-панель для тем карточек"""

    name = "Тема карточки"
    name_plural = "Темы карточек"
    icon = "fa-solid fa-tags"

    column_list = [CardTopic.id, CardTopic.topic, CardTopic.created_at]
    column_searchable_list = [CardTopic.topic]

    form_columns = [CardTopic.topic]

    can_create = True
    can_edit = True
    can_delete = True


class CardAdmin(ModelView, model=Card):
    """Админ-панель для карточек"""

    name = "Карточка"
    name_plural = "Карточки"
    icon = "fa-solid fa-id-card"

    column_list = [
        Card.id,
        Card.name,
        Card.subject_card,
        Card.grade,
        Card.quarter,
        Card.topic_id,
        Card.author_id,
        Card.created_at,
    ]
    column_searchable_list = [Card.name, Card.subject_card, Card.description]
    column_sortable_list = [Card.id, Card.name, Card.grade, Card.quarter, Card.created_at]
    column_default_sort = [(Card.id, True)]

    # Ограничиваем колонки в формах для избежания ошибки "Too many fields"
    form_columns = [
        Card.name,
        Card.description,
        Card.grade,
        Card.quarter,
        Card.subject_card,
        Card.file_path,
        Card.url,
        Card.iframe,
        Card.topic_id,
        Card.window_id,
        Card.author_id,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class QMJAdmin(ModelView, model=QMJ):
    """Админ-панель для ҚМЖ"""

    name = "ҚМЖ"
    name_plural = "ҚМЖ"
    icon = "fa-solid fa-calendar-alt"

    column_list = [
        QMJ.id,
        QMJ.title,
        QMJ.grade,
        QMJ.quarter,
        QMJ.code,
        QMJ.hour,
        QMJ.author_id,
        QMJ.created_at,
    ]
    column_searchable_list = [QMJ.title, QMJ.code, QMJ.text]
    column_sortable_list = [QMJ.id, QMJ.grade, QMJ.quarter, QMJ.order, QMJ.created_at]
    column_default_sort = [(QMJ.order, False), (QMJ.id, True)]

    # Ограничиваем колонки в формах
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
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class QMJFileAdmin(ModelView, model=QMJFile):
    """Админ-панель для файлов ҚМЖ"""

    name = "Файл ҚМЖ"
    name_plural = "Файлы ҚМЖ"
    icon = "fa-solid fa-file"

    column_list = [QMJFile.id, QMJFile.file, QMJFile.file_type, QMJFile.file_size, QMJFile.qmj_id]
    column_searchable_list = [QMJFile.file]

    form_columns = [
        QMJFile.qmj_id,
        QMJFile.file,
        QMJFile.file_type,
        QMJFile.file_size,
    ]

    can_create = True
    can_edit = True
    can_delete = True


class TestAdmin(ModelView, model=Test):
    """Админ-панель для тестов"""

    name = "Тест"
    name_plural = "Тесты"
    icon = "fa-solid fa-clipboard-check"

    column_list = [
        Test.id,
        Test.title,
        Test.subject,
        Test.difficulty,
        Test.duration,
        Test.user_id,
        Test.created_at,
    ]
    column_searchable_list = [Test.title, Test.subject]
    column_sortable_list = [Test.id, Test.title, Test.difficulty, Test.created_at]
    column_default_sort = [(Test.id, True)]

    # Ограничиваем колонки в формах
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


class QuestionAdmin(ModelView, model=Question):
    """Админ-панель для вопросов"""

    name = "Вопрос"
    name_plural = "Вопросы"
    icon = "fa-solid fa-question-circle"

    column_list = [Question.id, Question.text, Question.test_id, Question.order]
    column_searchable_list = [Question.text]
    column_sortable_list = [Question.id, Question.test_id, Question.order]

    # Ограничиваем колонки в формах
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
    """Админ-панель для ответов"""

    name = "Ответ"
    name_plural = "Ответы"
    icon = "fa-solid fa-check-circle"

    column_list = [Answer.id, Answer.text, Answer.is_correct, Answer.question_id]
    column_searchable_list = [Answer.text]
    column_sortable_list = [Answer.id, Answer.question_id]

    # Ограничиваем колонки в формах
    form_columns = [
        Answer.question_id,
        Answer.text,
        Answer.is_correct,
    ]

    page_size = 50
    page_size_options = [25, 50, 100, 200]

    can_create = True
    can_edit = True
    can_delete = True
