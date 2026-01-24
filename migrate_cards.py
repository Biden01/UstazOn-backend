#!/usr/bin/env python3
"""
Миграция карточек (Cards, CardTopics) из Django SQLite в FastAPI PostgreSQL
"""
import asyncio
import sqlite3
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.session import async_session_maker
from src.models import Card, CardTopic, Subject, InstitutionType


def get_sqlite_connection() -> sqlite3.Connection:
    """Подключение к SQLite базе Django"""
    db_path = Path(__file__).parent / "backend_old" / "UstazOn" / "db.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_card_topics(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Миграция тем карточек"""
    print("Миграция тем карточек...")
    cursor = sqlite_conn.execute("SELECT id, topic FROM MaterialsPage_cardtopic")

    topics_migrated = 0
    for row in cursor:
        existing = await db.execute(select(CardTopic).where(CardTopic.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        topic = CardTopic(id=row['id'], topic=row['topic'])
        db.add(topic)
        topics_migrated += 1

    await db.commit()
    print(f"✓ Мигрировано {topics_migrated} тем карточек")


async def migrate_cards(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Миграция карточек"""
    print("Миграция карточек...")
    cursor = sqlite_conn.execute("""
        SELECT id, name, description, grade, quarter, subject_card, file, url, iframe,
               img1_url, video1_url, video1_file, author_id, topic_id, window_id,
               created_at
        FROM MaterialsPage_card
    """)

    cards_migrated = 0
    for row in cursor:
        existing = await db.execute(select(Card).where(Card.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        card = Card(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            grade=row['grade'],
            quarter=row['quarter'],
            subject_card=row['subject_card'],
            file_path=row['file'],
            url=row['url'],
            iframe=bool(row['iframe']) if row['iframe'] is not None else True,
            img1_url=row['img1_url'],
            video1_url=row['video1_url'],
            video1_file_path=row['video1_file'],
            author_id=row['author_id'],
            topic_id=row['topic_id'],
            window_id=row['window_id'],
        )
        db.add(card)
        cards_migrated += 1

        if cards_migrated % 500 == 0:
            await db.commit()
            print(f"  Мигрировано {cards_migrated} карточек...")

    await db.commit()
    print(f"✓ Мигрировано {cards_migrated} карточек")

    # Связи карточка-предмет
    print("Миграция связей карточка-предмет...")
    cursor = sqlite_conn.execute("SELECT card_id, subject_id FROM MaterialsPage_card_subject")
    rel_count = 0
    for row in cursor:
        result = await db.execute(
            select(Card)
            .where(Card.id == row['card_id'])
            .options(selectinload(Card.subjects))
        )
        card = result.scalar_one_or_none()
        subject = await db.get(Subject, row['subject_id'])

        if card and subject:
            subj_ids = [s.id for s in card.subjects]
            if subject.id not in subj_ids:
                card.subjects.append(subject)
                rel_count += 1

    await db.commit()
    print(f"✓ Мигрировано {rel_count} связей карточка-предмет")

    # Связи карточка-тип учреждения
    print("Миграция связей карточка-учреждение...")
    cursor = sqlite_conn.execute("SELECT card_id, institutiontype_id FROM MaterialsPage_card_institution_type")
    rel_count = 0
    for row in cursor:
        result = await db.execute(
            select(Card)
            .where(Card.id == row['card_id'])
            .options(selectinload(Card.institution_types))
        )
        card = result.scalar_one_or_none()
        inst = await db.get(InstitutionType, row['institutiontype_id'])

        if card and inst:
            inst_ids = [it.id for it in card.institution_types]
            if inst.id not in inst_ids:
                card.institution_types.append(inst)
                rel_count += 1

    await db.commit()
    print(f"✓ Мигрировано {rel_count} связей карточка-учреждение")


async def main():
    """Основная функция миграции"""
    print("=" * 60)
    print("Миграция карточек: Django SQLite → FastAPI PostgreSQL")
    print("=" * 60)

    sqlite_conn = get_sqlite_connection()
    print("Подключено к SQLite")

    async with async_session_maker() as db:
        print("Подключено к PostgreSQL")
        print()

        try:
            await migrate_card_topics(db, sqlite_conn)
            await migrate_cards(db, sqlite_conn)

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
