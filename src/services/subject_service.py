from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Subject, InstitutionType, Template, Window
from src.schemas.subject import SubjectCreate, SubjectUpdate


async def get_subjects(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Subject]:
    """Get list of subjects with institution types"""
    result = await db.execute(
        select(Subject)
        .options(
            selectinload(Subject.institution_types),
            selectinload(Subject.windows).selectinload(Window.template),
        )
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_subject_by_id(db: AsyncSession, subject_id: int) -> Subject | None:
    """Get subject by ID with related data"""
    result = await db.execute(
        select(Subject)
        .options(
            selectinload(Subject.institution_types),
            selectinload(Subject.windows).selectinload(Window.template),
        )
        .where(Subject.id == subject_id)
    )
    return result.scalar_one_or_none()


async def get_subject_by_code(db: AsyncSession, code: str) -> Subject | None:
    """Get subject by code"""
    result = await db.execute(
        select(Subject)
        .options(
            selectinload(Subject.institution_types),
            selectinload(Subject.windows).selectinload(Window.template),
        )
        .where(Subject.code == code)
    )
    return result.scalar_one_or_none()


async def create_subject(db: AsyncSession, subject_data: SubjectCreate) -> Subject:
    """Create new subject"""
    # Get institution types if provided
    institution_types = []
    if subject_data.institution_type_ids:
        result = await db.execute(
            select(InstitutionType).where(
                InstitutionType.id.in_(subject_data.institution_type_ids)
            )
        )
        institution_types = list(result.scalars().all())

    # Get windows if provided
    windows = []
    if subject_data.window_ids:
        result = await db.execute(
            select(Window).where(Window.id.in_(subject_data.window_ids))
        )
        windows = list(result.scalars().all())

    subject = Subject(
        name=subject_data.name,
        code=subject_data.code,
        image_url=subject_data.image_url,
        hero_image_url=subject_data.hero_image_url,
        institution_types=institution_types,
        windows=windows,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject


async def update_subject(
    db: AsyncSession, subject: Subject, subject_data: SubjectUpdate
) -> Subject:
    """Update subject"""
    if subject_data.name is not None:
        subject.name = subject_data.name
    if subject_data.code is not None:
        subject.code = subject_data.code
    if subject_data.image_url is not None:
        subject.image_url = subject_data.image_url
    if subject_data.hero_image_url is not None:
        subject.hero_image_url = subject_data.hero_image_url

    if subject_data.institution_type_ids is not None:
        result = await db.execute(
            select(InstitutionType).where(
                InstitutionType.id.in_(subject_data.institution_type_ids)
            )
        )
        subject.institution_types = list(result.scalars().all())

    if subject_data.window_ids is not None:
        result = await db.execute(
            select(Window).where(Window.id.in_(subject_data.window_ids))
        )
        subject.windows = list(result.scalars().all())

    await db.commit()
    await db.refresh(subject)
    return subject


async def delete_subject(db: AsyncSession, subject: Subject) -> None:
    """Delete subject"""
    await db.delete(subject)
    await db.commit()


# InstitutionType services
async def get_institution_types(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[InstitutionType]:
    """Get list of institution types"""
    result = await db.execute(
        select(InstitutionType).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_institution_type_by_id(
    db: AsyncSession, institution_type_id: int
) -> InstitutionType | None:
    """Get institution type by ID"""
    result = await db.execute(
        select(InstitutionType).where(InstitutionType.id == institution_type_id)
    )
    return result.scalar_one_or_none()


# Template services
async def get_templates(db: AsyncSession) -> list[Template]:
    """Get all templates"""
    result = await db.execute(select(Template))
    return list(result.scalars().all())


async def get_template_by_id(db: AsyncSession, template_id: int) -> Template | None:
    """Get template by ID"""
    result = await db.execute(select(Template).where(Template.id == template_id))
    return result.scalar_one_or_none()


# Window services
async def get_windows(db: AsyncSession) -> list[Window]:
    """Get all windows"""
    result = await db.execute(
        select(Window).options(selectinload(Window.template))
    )
    return list(result.scalars().all())


async def get_window_by_id(db: AsyncSession, window_id: int) -> Window | None:
    """Get window by ID"""
    result = await db.execute(
        select(Window)
        .options(selectinload(Window.template), selectinload(Window.subjects))
        .where(Window.id == window_id)
    )
    return result.scalar_one_or_none()


# InstitutionType CRUD
async def create_institution_type(
    db: AsyncSession, name: str, code: str | None = None
) -> InstitutionType:
    """Create new institution type"""
    institution_type = InstitutionType(name=name, code=code)
    db.add(institution_type)
    await db.commit()
    await db.refresh(institution_type)
    return institution_type


async def update_institution_type(
    db: AsyncSession, institution_type: InstitutionType, name: str | None = None, code: str | None = None
) -> InstitutionType:
    """Update institution type"""
    if name is not None:
        institution_type.name = name
    if code is not None:
        institution_type.code = code
    await db.commit()
    await db.refresh(institution_type)
    return institution_type


async def delete_institution_type(db: AsyncSession, institution_type: InstitutionType) -> None:
    """Delete institution type"""
    await db.delete(institution_type)
    await db.commit()


# Template CRUD
async def create_template(
    db: AsyncSession, name: str, code_name: str
) -> Template:
    """Create new template"""
    template = Template(name=name, code_name=code_name)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(
    db: AsyncSession, template: Template, name: str | None = None, code_name: str | None = None
) -> Template:
    """Update template"""
    if name is not None:
        template.name = name
    if code_name is not None:
        template.code_name = code_name
    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(db: AsyncSession, template: Template) -> None:
    """Delete template"""
    await db.delete(template)
    await db.commit()


# Window CRUD
async def create_window(
    db: AsyncSession,
    name: str,
    template_id: int | None = None,
    link: str | None = None,
    nsub: bool = False,
    image_url: str | None = None,
    subject_ids: list[int] | None = None,
) -> Window:
    """Create new window"""
    subjects = []
    if subject_ids:
        result = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))
        subjects = list(result.scalars().all())
    
    window = Window(
        name=name,
        template_id=template_id,
        link=link,
        nsub=nsub,
        image_url=image_url,
        subjects=subjects,
    )
    db.add(window)
    await db.commit()
    await db.refresh(window)
    return window


async def update_window(
    db: AsyncSession,
    window: Window,
    name: str | None = None,
    template_id: int | None = None,
    link: str | None = None,
    nsub: bool | None = None,
    image_url: str | None = None,
    subject_ids: list[int] | None = None,
) -> Window:
    """Update window"""
    if name is not None:
        window.name = name
    if template_id is not None:
        window.template_id = template_id
    if link is not None:
        window.link = link
    if nsub is not None:
        window.nsub = nsub
    if image_url is not None:
        window.image_url = image_url
    if subject_ids is not None:
        result = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))
        window.subjects = list(result.scalars().all())
    
    await db.commit()
    await db.refresh(window)
    return window


async def delete_window(db: AsyncSession, window: Window) -> None:
    """Delete window"""
    await db.delete(window)
    await db.commit()

