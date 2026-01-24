#!/usr/bin/env python3
"""
Миграция пользователей (Users) из Django SQLite в FastAPI PostgreSQL
"""
import asyncio
import sqlite3
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_maker
from src.models import User


def get_sqlite_connection() -> sqlite3.Connection:
    """Подключение к SQLite базе Django"""
    db_path = Path(__file__).parent / "backend_old" / "UstazOn" / "db.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_users(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Миграция пользователей"""
    print("Миграция пользователей...")
    cursor = sqlite_conn.execute("""
        SELECT id, username, email, first_name, last_name, is_active,
               name, phone, avatar, password
        FROM AuthPage_user
    """)

    users_migrated = 0
    used_phones = set()
    used_iins = set()

    for row in cursor:
        # Проверка существующего пользователя
        existing = await db.execute(select(User).where(User.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        # Обработка уникальности телефона
        phone = row['phone'] if row['phone'] else f"+7{row['id']:010d}"
        if phone in used_phones or not phone:
            phone = f"+7{row['id']:010d}"

        if phone in used_phones:
            phone = f"{phone}_{row['id']}"

        used_phones.add(phone)

        # Генерация уникального ИИН (12 цифр)
        iin = f"{row['id']:012d}"
        counter = 0
        while iin in used_iins:
            counter += 1
            iin = f"{(row['id'] * 1000 + counter):012d}"

        used_iins.add(iin)

        user = User(
            id=row['id'],
            iin=iin,
            name=row['name'] if row['name'] else row['first_name'],
            phone=phone,
            hashed_password=row['password'] if row['password'] else '',
            is_active=bool(row['is_active']),
            is_verified=True,
        )
        db.add(user)
        users_migrated += 1

        if users_migrated % 100 == 0:
            await db.commit()
            print(f"  Мигрировано {users_migrated} пользователей...")

    await db.commit()
    print(f"✓ Мигрировано {users_migrated} пользователей")

    # Исправление последовательности после миграции
    if users_migrated > 0:
        print("  Исправление последовательности users...")
        result = await db.execute(text("SELECT MAX(id) FROM users"))
        max_id = result.scalar()
        if max_id:
            await db.execute(text(f"SELECT setval('users_id_seq', {max_id}, true)"))
            await db.commit()
            print(f"  ✓ Последовательность сброшена до {max_id}")


async def main():
    """Основная функция миграции"""
    print("=" * 60)
    print("Миграция пользователей: Django SQLite → FastAPI PostgreSQL")
    print("=" * 60)

    sqlite_conn = get_sqlite_connection()
    print(f"Подключено к SQLite: {sqlite_conn}")

    async with async_session_maker() as db:
        print("Подключено к PostgreSQL")
        print()

        try:
            await migrate_users(db, sqlite_conn)

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
