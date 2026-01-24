from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_current_superuser, get_db
from src.models.user import User
from src.schemas.subject import (
    SubjectResponse,
    SubjectCreate,
    SubjectUpdate,
    InstitutionTypeResponse,
    InstitutionTypeCreate,
    InstitutionTypeUpdate,
    TemplateResponse,
    TemplateCreate,
    TemplateUpdate,
    WindowResponse,
    WindowCreate,
    WindowUpdate,
)
from src.services import subject_service

router = APIRouter(prefix="/subjects", tags=["subjects"])


# Subject endpoints
@router.get("", response_model=list[SubjectResponse])
async def get_subjects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all subjects"""
    subjects = await subject_service.get_subjects(db, skip=skip, limit=limit)
    return subjects


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get subject by ID"""
    subject = await subject_service.get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предмет не найден",
        )
    return subject


@router.get("/code/{code}", response_model=SubjectResponse)
async def get_subject_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Get subject by code"""
    subject = await subject_service.get_subject_by_code(db, code)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предмет не найден",
        )
    return subject


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    subject_data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Create new subject (superadmin only)"""
    existing = await subject_service.get_subject_by_code(db, subject_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Предмет с таким кодом уже существует",
        )

    subject = await subject_service.create_subject(db, subject_data)
    return subject


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: int,
    subject_data: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Update subject (superadmin only)"""
    subject = await subject_service.get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предмет не найден",
        )

    if subject_data.code and subject_data.code != subject.code:
        existing = await subject_service.get_subject_by_code(db, subject_data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Предмет с таким кодом уже существует",
            )

    updated_subject = await subject_service.update_subject(db, subject, subject_data)
    return updated_subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Delete subject (superadmin only)"""
    subject = await subject_service.get_subject_by_id(db, subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Предмет не найден",
        )

    await subject_service.delete_subject(db, subject)


# InstitutionType endpoints
@router.get("/institution-types/", response_model=list[InstitutionTypeResponse])
async def get_institution_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get list of institution types"""
    institution_types = await subject_service.get_institution_types(
        db, skip=skip, limit=limit
    )
    return institution_types


@router.get("/institution-types/{institution_type_id}", response_model=InstitutionTypeResponse)
async def get_institution_type(
    institution_type_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get institution type by ID"""
    institution_type = await subject_service.get_institution_type_by_id(
        db, institution_type_id
    )
    if not institution_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тип учреждения не найден",
        )
    return institution_type


@router.post("/institution-types/", response_model=InstitutionTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_institution_type(
    data: InstitutionTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Create new institution type (superadmin only)"""
    institution_type = await subject_service.create_institution_type(
        db, name=data.name, code=data.code
    )
    return institution_type


@router.put("/institution-types/{institution_type_id}", response_model=InstitutionTypeResponse)
async def update_institution_type(
    institution_type_id: int,
    data: InstitutionTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Update institution type (superadmin only)"""
    institution_type = await subject_service.get_institution_type_by_id(db, institution_type_id)
    if not institution_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тип учреждения не найден",
        )
    updated = await subject_service.update_institution_type(
        db, institution_type, name=data.name, code=data.code
    )
    return updated


@router.delete("/institution-types/{institution_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_institution_type(
    institution_type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Delete institution type (superadmin only)"""
    institution_type = await subject_service.get_institution_type_by_id(db, institution_type_id)
    if not institution_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тип учреждения не найден",
        )
    await subject_service.delete_institution_type(db, institution_type)


# Template endpoints
@router.get("/templates/", response_model=list[TemplateResponse])
async def get_templates(db: AsyncSession = Depends(get_db)):
    """Get all templates"""
    templates = await subject_service.get_templates(db)
    return templates


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get template by ID"""
    template = await subject_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаблон не найден",
        )
    return template


@router.post("/templates/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Create new template (superadmin only)"""
    template = await subject_service.create_template(db, name=data.name, code_name=data.code_name)
    return template


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Update template (superadmin only)"""
    template = await subject_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаблон не найден",
        )
    updated = await subject_service.update_template(db, template, name=data.name, code_name=data.code_name)
    return updated


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Delete template (superadmin only)"""
    template = await subject_service.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шаблон не найден",
        )
    await subject_service.delete_template(db, template)


# Window endpoints
@router.get("/windows/", response_model=list[WindowResponse])
async def get_windows(db: AsyncSession = Depends(get_db)):
    """Get all windows"""
    windows = await subject_service.get_windows(db)
    return windows


@router.get("/windows/{window_id}", response_model=WindowResponse)
async def get_window(
    window_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get window by ID"""
    window = await subject_service.get_window_by_id(db, window_id)
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Окно не найдено",
        )
    return window


@router.post("/windows/", response_model=WindowResponse, status_code=status.HTTP_201_CREATED)
async def create_window(
    data: WindowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Create new window (superadmin only)"""
    window = await subject_service.create_window(
        db,
        name=data.name,
        template_id=data.template_id,
        link=data.link,
        nsub=data.nsub,
        image_url=data.image_url,
        subject_ids=data.subject_ids,
    )
    return window


@router.put("/windows/{window_id}", response_model=WindowResponse)
async def update_window(
    window_id: int,
    data: WindowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Update window (superadmin only)"""
    window = await subject_service.get_window_by_id(db, window_id)
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Окно не найдено",
        )
    updated = await subject_service.update_window(
        db,
        window,
        name=data.name,
        template_id=data.template_id,
        link=data.link,
        nsub=data.nsub,
        image_url=data.image_url,
        subject_ids=data.subject_ids,
    )
    return updated


@router.delete("/windows/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_window(
    window_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Delete window (superadmin only)"""
    window = await subject_service.get_window_by_id(db, window_id)
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Окно не найдено",
        )
    await subject_service.delete_window(db, window)

