#!/usr/bin/env python3
"""
Миграция предметов и типов учреждений (Subjects, InstitutionTypes) из Django SQLite в FastAPI PostgreSQL
"""
import asyncio
import sqlite3
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.session import async_session_maker
from src.models import Subject, InstitutionType


def get_sqlite_connection() -> sqlite3.Connection:
    """Подключение к SQLite базе Django"""
    db_path = Path(__file__).parent.parent / "backend_old" / "UstazOn" / "db.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_subjects_and_institutions(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Миграция предметов и типов учреждений"""

    # Типы учреждений
    print("Миграция типов учреждений...")
    cursor = sqlite_conn.execute("SELECT id, name FROM SubjectPage_institutiontype")
    inst_migrated = 0
    for row in cursor:
        existing = await db.execute(select(InstitutionType).where(InstitutionType.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        inst_type = InstitutionType(id=row['id'], name=row['name'])
        db.add(inst_type)
        inst_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {inst_migrated} типов учреждений")

    # Предметы
    print("Миграция предметов...")
    cursor = sqlite_conn.execute("SELECT id, name, code, image_url, hero_image_url FROM SubjectPage_subject")
    subj_migrated = 0
    used_codes = set()

    for row in cursor:
        existing = await db.execute(select(Subject).where(Subject.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        # Обработка дубликатов кодов предметов
        code = row['code']
        if code and code in used_codes:
            code = f"{code}_{row['id']}"

        if code:
            used_codes.add(code)

        subject = Subject(
            id=row['id'],
            name=row['name'],
            code=code,
            image_url=row['image_url'],
            hero_image_url=row['hero_image_url'],
        )
        db.add(subject)
        subj_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {subj_migrated} предметов")

    # Связи предмет-тип учреждения
    print("Миграция связей предмет-учреждение...")
    cursor = sqlite_conn.execute("""
        SELECT subject_id, institutiontype_id
        FROM SubjectPage_subject_institution_type
    """)
    rel_count = 0
    for row in cursor:
        result = await db.execute(
            select(Subject)
            .where(Subject.id == row['subject_id'])
            .options(selectinload(Subject.institution_types))
        )
        subject = result.scalar_one_or_none()

        inst = await db.get(InstitutionType, row['institutiontype_id'])

        if subject and inst:
            inst_ids = [it.id for it in subject.institution_types]
            if inst.id not in inst_ids:
                subject.institution_types.append(inst)
                rel_count += 1

    await db.commit()
    print(f"✓ Мигрировано {rel_count} связей предмет-учреждение")


async def main():
    """Основная функция миграции"""
    print("=" * 60)
    print("Миграция предметов: Django SQLite → FastAPI PostgreSQL")
    print("=" * 60)

    sqlite_conn = get_sqlite_connection()
    print(f"Подключено к SQLite")

    async with async_session_maker() as db:
        print("Подключено к PostgreSQL")
        print()

        try:
            await migrate_subjects_and_institutions(db, sqlite_conn)

            print()
            print("=" * 60)
            print("✓ Миграция завершена успешно!")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Ошибка миграции: {e}")
            raise
        finally:
            sqlite_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
