#!/usr/bin/env python3
"""
Скрипт для исправления изображений карточек (Card.img1_url)
Берет данные из старой базы SQLite и обновляет img1_url в PostgreSQL
"""
import asyncio
import sqlite3
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_maker
from src.models import Card


def get_sqlite_connection() -> sqlite3.Connection:
    """Подключение к SQLite базе Django"""
    # Путь к старой базе
    db_path = Path(__file__).parent.parent / "backend_old" / "UstazOn" / "db.sqlite3"
    print(f"Подключение к SQLite: {db_path}")
    
    if not db_path.exists():
        raise FileNotFoundError(f"Файл базы данных не найден: {db_path}")
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def fix_card_images(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Обновление изображений карточек"""
    print("Начало проверки изображений карточек...")
    
    # Получаем все карточки из старой базы у которых есть img1
    cursor = sqlite_conn.execute("""
        SELECT id, img1 
        FROM MaterialsPage_card 
        WHERE img1 IS NOT NULL AND img1 != ''
    """)
    
    updated_count = 0
    checked_count = 0
    
    for row in cursor:
        checked_count += 1
        card_id = row['id']
        img1_path = row['img1']
        
        # Проверяем существование карточки в новой базе
        result = await db.execute(select(Card).where(Card.id == card_id))
        card = result.scalar_one_or_none()
        
        if not card:
            continue
            
        # Если у карточки нет img1_url, но есть img1 в старой базе
        if not card.img1_url:
            # Формируем URL для медиа файла
            # В Django img1 хранится как путь относительно media root, например: cards/image/file.jpg
            # Мы будем раздавать папку media по пути /media/
            
            # Убедимся что путь не начинается с слеша
            clean_path = img1_path.lstrip('/')
            new_url = f"/media/{clean_path}"
            
            card.img1_url = new_url
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"Обновлено {updated_count} карточек...")
                await db.commit()

    await db.commit()
    print(f"Проверено {checked_count} записей из старой БД")
    print(f"✓ Обновлено {updated_count} карточек с отсутствующими изображениями")


async def main():
    """Основная функция"""
    print("=" * 60)
    print("Исправление изображений карточек")
    print("=" * 60)

    try:
        sqlite_conn = get_sqlite_connection()
        print("Подключено к SQLite")

        async with async_session_maker() as db:
            print("Подключено к PostgreSQL")
            print()
            
            await fix_card_images(db, sqlite_conn)

            print()
            print("=" * 60)
            print("✓ Исправление завершено успешно!")
            print("=" * 60)

    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
