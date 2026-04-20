#!/usr/bin/env python3
"""
Миграция ҚМЖ (QMJ - календарные планы) из Django SQLite в FastAPI PostgreSQL
"""
import asyncio
import sqlite3
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.session import async_session_maker
from src.models import QMJ, Subject, InstitutionType


def get_sqlite_connection() -> sqlite3.Connection:
    """Подключение к SQLite базе Django"""
    db_path = Path(__file__).parent.parent / "backend_old" / "UstazOn" / "db.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_qmj(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Миграция ҚМЖ (календарных планов)"""
    print("Миграция ҚМЖ...")
    cursor = sqlite_conn.execute("""
        SELECT id, grade, quarter, code, title, text, hour, "order", file, author_id, created_at, updated_at
        FROM QmjPage_qmj
    """)

    qmj_migrated = 0
    for row in cursor:
        existing = await db.execute(select(QMJ).where(QMJ.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        # Преобразуем строки в числа
        grade = int(row['grade']) if row['grade'] and str(row['grade']).isdigit() else None
        quarter = int(row['quarter']) if row['quarter'] and str(row['quarter']).isdigit() else None
        hour = int(row['hour']) if row['hour'] and str(row['hour']).isdigit() else 1
        order = int(row['order']) if row['order'] and str(row['order']).isdigit() else 0

        qmj = QMJ(
            id=row['id'],
            grade=grade,
            quarter=quarter,
            code=row['code'],
            title=row['title'],
            text=row['text'],
            hour=hour,
            order=order,
            file=row['file'],
            author_id=row['author_id'],
        )
        db.add(qmj)
        qmj_migrated += 1

        if qmj_migrated % 500 == 0:
            await db.commit()
            print(f"  Мигрировано {qmj_migrated} ҚМЖ...")

    await db.commit()
    print(f"✓ Мигрировано {qmj_migrated} ҚМЖ")

    # Связи ҚМЖ-предмет
    print("Миграция связей ҚМЖ-предмет...")
    cursor = sqlite_conn.execute("SELECT qmj_id, subject_id FROM QmjPage_qmj_subject")
    rel_count = 0
    for row in cursor:
        result = await db.execute(
            select(QMJ)
            .where(QMJ.id == row['qmj_id'])
            .options(selectinload(QMJ.subjects))
        )
        qmj = result.scalar_one_or_none()
        subject = await db.get(Subject, row['subject_id'])

        if qmj and subject:
            subj_ids = [s.id for s in qmj.subjects]
            if subject.id not in subj_ids:
                qmj.subjects.append(subject)
                rel_count += 1

    await db.commit()
    print(f"✓ Мигрировано {rel_count} связей ҚМЖ-предмет")

    # Связи ҚМЖ-тип учреждения
    print("Миграция связей ҚМЖ-учреждение...")
    cursor = sqlite_conn.execute("SELECT qmj_id, institutiontype_id FROM QmjPage_qmj_institution_type")
    rel_count = 0
    for row in cursor:
        result = await db.execute(
            select(QMJ)
            .where(QMJ.id == row['qmj_id'])
            .options(selectinload(QMJ.institution_types))
        )
        qmj = result.scalar_one_or_none()
        inst = await db.get(InstitutionType, row['institutiontype_id'])

        if qmj and inst:
            inst_ids = [it.id for it in qmj.institution_types]
            if inst.id not in inst_ids:
                qmj.institution_types.append(inst)
                rel_count += 1

    await db.commit()
    print(f"✓ Мигрировано {rel_count} связей ҚМЖ-учреждение")


async def main():
    """Основная функция миграции"""
    print("=" * 60)
    print("Миграция ҚМЖ: Django SQLite → FastAPI PostgreSQL")
    print("=" * 60)

    sqlite_conn = get_sqlite_connection()
    print("Подключено к SQLite")

    async with async_session_maker() as db:
        print("Подключено к PostgreSQL")
        print()

        try:
            await migrate_qmj(db, sqlite_conn)

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
