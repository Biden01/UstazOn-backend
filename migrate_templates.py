#!/usr/bin/env python3
"""
Миграция шаблонов и окон (Templates, Windows) из Django SQLite в FastAPI PostgreSQL
"""
import asyncio
import sqlite3
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_maker
from src.models import Template, Window


def get_sqlite_connection() -> sqlite3.Connection:
    """Подключение к SQLite базе Django"""
    db_path = Path(__file__).parent / "backend_old" / "UstazOn" / "db.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_templates_and_windows(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Миграция шаблонов и окон"""

    # Шаблоны
    print("Миграция шаблонов...")
    cursor = sqlite_conn.execute("SELECT id, code_name, name FROM TemplatesPage_template")

    templates_migrated = 0
    for row in cursor:
        existing = await db.execute(select(Template).where(Template.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        template = Template(
            id=row['id'],
            name=row['name'],
            code_name=row['code_name']
        )
        db.add(template)
        templates_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {templates_migrated} шаблонов")

    # Окна
    print("Миграция окон...")
    cursor = sqlite_conn.execute("""
        SELECT id, template_id, nsub, image_url, link, name
        FROM TemplatesPage_window
    """)

    windows_migrated = 0
    for row in cursor:
        existing = await db.execute(select(Window).where(Window.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        window = Window(
            id=row['id'],
            template_id=row['template_id'],
            nsub=bool(row['nsub']),
            image_url=row['image_url'],
            link=row['link'],
            name=row['name']
        )
        db.add(window)
        windows_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {windows_migrated} окон")


async def main():
    """Основная функция миграции"""
    print("=" * 60)
    print("Миграция шаблонов и окон: Django SQLite → FastAPI PostgreSQL")
    print("=" * 60)

    sqlite_conn = get_sqlite_connection()
    print("Подключено к SQLite")

    async with async_session_maker() as db:
        print("Подключено к PostgreSQL")
        print()

        try:
            await migrate_templates_and_windows(db, sqlite_conn)

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
