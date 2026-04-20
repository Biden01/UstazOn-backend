#!/usr/bin/env python3
"""
Миграция тестов (Tests, Questions, Answers) из Django SQLite в FastAPI PostgreSQL
"""
import asyncio
import sqlite3
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_maker
from src.models import Test, Question, Answer


def get_sqlite_connection() -> sqlite3.Connection:
    """Подключение к SQLite базе Django"""
    db_path = Path(__file__).parent.parent / "backend_old" / "UstazOn" / "db.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_tests(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Миграция тестов, вопросов и ответов"""

    # Тесты
    print("Миграция тестов...")
    cursor = sqlite_conn.execute("""
        SELECT id, title, subject, duration, difficulty, user_id
        FROM TestPage_test
    """)

    tests_migrated = 0
    for row in cursor:
        existing = await db.execute(select(Test).where(Test.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        test = Test(
            id=row['id'],
            title=row['title'],
            subject=row['subject'],
            duration=row['duration'] if row['duration'] else 30,
            difficulty=row['difficulty'] if row['difficulty'] else 'medium',
            user_id=row['user_id'],
        )
        db.add(test)
        tests_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {tests_migrated} тестов")

    # Вопросы
    print("Миграция вопросов...")
    cursor = sqlite_conn.execute("""
        SELECT id, text, photo, video, test_id
        FROM TestPage_question
    """)

    questions_migrated = 0
    for row in cursor:
        existing = await db.execute(select(Question).where(Question.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        question = Question(
            id=row['id'],
            test_id=row['test_id'],
            text=row['text'],
            photo=row['photo'],
            video=row['video'],
        )
        db.add(question)
        questions_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {questions_migrated} вопросов")

    # Ответы
    print("Миграция ответов...")
    cursor = sqlite_conn.execute("""
        SELECT id, text, is_correct, question_id
        FROM TestPage_answer
    """)

    answers_migrated = 0
    for row in cursor:
        existing = await db.execute(select(Answer).where(Answer.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        answer = Answer(
            id=row['id'],
            question_id=row['question_id'],
            text=row['text'],
            is_correct=bool(row['is_correct']),
        )
        db.add(answer)
        answers_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {answers_migrated} ответов")


async def main():
    """Основная функция миграции"""
    print("=" * 60)
    print("Миграция тестов: Django SQLite → FastAPI PostgreSQL")
    print("=" * 60)

    sqlite_conn = get_sqlite_connection()
    print("Подключено к SQLite")

    async with async_session_maker() as db:
        print("Подключено к PostgreSQL")
        print()

        try:
            await migrate_tests(db, sqlite_conn)

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
