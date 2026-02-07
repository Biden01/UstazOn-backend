from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.qmj import QMJ, QMJFile
from src.models.subject import Subject, InstitutionType
from src.schemas.qmj import QMJCreate, QMJUpdate, QMJFileCreate


# QMJ CRUD
async def get_qmj_list(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    grade: int | None = None,
    quarter: int | None = None,
    code: str | None = None,
    author_id: int | None = None,
) -> list[QMJ]:
    """Get QMJ list with optional filters.

    The 'code' parameter filters by subject code through the qmj_subjects relationship,
    not by the QMJ.code field directly.
    """
    query = select(QMJ).options(
        selectinload(QMJ.subjects),
        selectinload(QMJ.institution_types),
        selectinload(QMJ.files),
    )

    # Apply filters
    filters = []
    if grade is not None:
        filters.append(QMJ.grade == grade)
    if quarter is not None:
        filters.append(QMJ.quarter == quarter)
    if author_id is not None:
        filters.append(QMJ.author_id == author_id)

    if filters:
        query = query.where(and_(*filters))

    # Filter by subject code through relationship
    if code is not None:
        query = query.join(QMJ.subjects).where(Subject.code == code)

    # Order by quarter and order number
    query = query.order_by(QMJ.quarter, QMJ.order, QMJ.id).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.unique().scalars().all())


async def get_qmj_by_id(db: AsyncSession, qmj_id: int) -> QMJ | None:
    """Get QMJ by ID with all relationships"""
    result = await db.execute(
        select(QMJ)
        .where(QMJ.id == qmj_id)
        .options(
            selectinload(QMJ.subjects),
            selectinload(QMJ.institution_types),
            selectinload(QMJ.files).selectinload(QMJFile.uploaded_by),
            selectinload(QMJ.author),
        )
    )
    return result.scalar_one_or_none()


async def create_qmj(db: AsyncSession, qmj_data: QMJCreate, author_id: int) -> QMJ:
    """Create new QMJ"""
    # Extract many-to-many IDs
    subject_ids = qmj_data.subject_ids
    institution_type_ids = qmj_data.institution_type_ids

    # Create QMJ without many-to-many fields
    qmj_dict = qmj_data.model_dump(exclude={"subject_ids", "institution_type_ids"})
    qmj = QMJ(**qmj_dict, author_id=author_id)

    # Add subjects
    if subject_ids:
        subjects = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))
        qmj.subjects = list(subjects.scalars().all())

    # Add institution types
    if institution_type_ids:
        institution_types = await db.execute(
            select(InstitutionType).where(InstitutionType.id.in_(institution_type_ids))
        )
        qmj.institution_types = list(institution_types.scalars().all())

    db.add(qmj)
    await db.commit()
    await db.refresh(qmj)
    return qmj


async def update_qmj(
    db: AsyncSession, qmj_id: int, qmj_data: QMJUpdate
) -> QMJ | None:
    """Update QMJ"""
    qmj = await get_qmj_by_id(db, qmj_id)
    if not qmj:
        return None

    update_data = qmj_data.model_dump(exclude_unset=True)

    # Handle many-to-many updates
    subject_ids = update_data.pop("subject_ids", None)
    institution_type_ids = update_data.pop("institution_type_ids", None)

    # Update scalar fields
    for field, value in update_data.items():
        setattr(qmj, field, value)

    # Update subjects
    if subject_ids is not None:
        subjects = await db.execute(select(Subject).where(Subject.id.in_(subject_ids)))
        qmj.subjects = list(subjects.scalars().all())

    # Update institution types
    if institution_type_ids is not None:
        institution_types = await db.execute(
            select(InstitutionType).where(InstitutionType.id.in_(institution_type_ids))
        )
        qmj.institution_types = list(institution_types.scalars().all())

    await db.commit()
    await db.refresh(qmj)
    return qmj


async def delete_qmj(db: AsyncSession, qmj_id: int) -> bool:
    """Delete QMJ (cascade deletes files)"""
    qmj = await get_qmj_by_id(db, qmj_id)
    if not qmj:
        return False

    await db.delete(qmj)
    await db.commit()
    return True


# QMJFile CRUD
async def add_file_to_qmj(
    db: AsyncSession, qmj_id: int, file_data: QMJFileCreate, user_id: int
) -> QMJFile | None:
    """Add file attachment to QMJ"""
    qmj = await get_qmj_by_id(db, qmj_id)
    if not qmj:
        return None

    qmj_file = QMJFile(
        **file_data.model_dump(), qmj_id=qmj_id, uploaded_by_id=user_id
    )
    db.add(qmj_file)
    await db.commit()
    await db.refresh(qmj_file)
    return qmj_file


async def delete_qmj_file(db: AsyncSession, file_id: int) -> bool:
    """Delete QMJ file attachment"""
    result = await db.execute(select(QMJFile).where(QMJFile.id == file_id))
    qmj_file = result.scalar_one_or_none()
    if not qmj_file:
        return False

    await db.delete(qmj_file)
    await db.commit()
    return True


async def get_qmj_by_quarter(
    db: AsyncSession, quarter: int, grade: int | None = None, code: str | None = None
) -> list[QMJ]:
    """Get all QMJ for a specific quarter, optionally filtered by grade and subject code.

    The 'code' parameter filters by subject code through the qmj_subjects relationship.
    """
    query = select(QMJ).where(QMJ.quarter == quarter)

    if grade is not None:
        query = query.where(QMJ.grade == grade)

    # Filter by subject code through relationship
    if code is not None:
        query = query.join(QMJ.subjects).where(Subject.code == code)

    query = query.order_by(QMJ.order, QMJ.id).options(
        selectinload(QMJ.subjects),
        selectinload(QMJ.institution_types),
        selectinload(QMJ.files),
    )

    result = await db.execute(query)
    return list(result.unique().scalars().all())
