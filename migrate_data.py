"""
Data migration script from Django SQLite to FastAPI PostgreSQL
Мигрирует данные из старой базы Django (SQLite) в новую FastAPI (PostgreSQL)
"""
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.session import async_session_maker
from src.models import (
    User,
    Subject,
    InstitutionType,
    Template,
    Window,
    Card,
    CardTopic,
    Test,
    Question,
    Answer,
    QMJ,
    QMJFile,
)

# Path to old SQLite database
SQLITE_DB = Path(__file__).parent.parent / "backend_old" / "UstazOn" / "db.sqlite3"


def get_sqlite_connection():
    """Get SQLite connection"""
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate_users(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate users from Django to FastAPI"""
    print("Migrating users...")
    cursor = sqlite_conn.execute("""
        SELECT id, username, email, first_name, last_name, is_active,
               name, phone, avatar, password
        FROM AuthPage_user
    """)

    users_migrated = 0
    used_phones = set()
    used_iins = set()

    for row in cursor:
        # Check if user already exists
        existing = await db.execute(select(User).where(User.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        # Use phone or generate a fake one, ensuring uniqueness
        phone = row['phone'] if row['phone'] else f"+7{row['id']:010d}"
        if phone in used_phones or not phone:
            # If duplicate or empty, use user ID to make it unique
            phone = f"+7{row['id']:010d}"

        # If still duplicate (shouldn't happen with user ID), append suffix
        if phone in used_phones:
            phone = f"{phone}_{row['id']}"

        used_phones.add(phone)

        # Generate fake IIN (12 digits), ensuring uniqueness
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
            hashed_password=row['password'] if row['password'] else '',  # Django password hash
            is_active=bool(row['is_active']),
            is_verified=True,  # Set all migrated users as verified
        )
        db.add(user)
        users_migrated += 1

        if users_migrated % 100 == 0:
            await db.commit()
            print(f"  Migrated {users_migrated} users...")

    await db.commit()
    print(f"✓ Migrated {users_migrated} users")

    # Fix the sequence after migration
    if users_migrated > 0:
        print("  Fixing users sequence...")
        result = await db.execute(text("SELECT MAX(id) FROM users"))
        max_id = result.scalar()
        if max_id:
            await db.execute(text(f"SELECT setval('users_id_seq', {max_id}, true)"))
            await db.commit()
            print(f"  ✓ Sequence reset to {max_id}")


async def migrate_subjects_and_institutions(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate subjects and institution types"""
    print("Migrating institution types...")

    # Institution types
    cursor = sqlite_conn.execute("SELECT id, name FROM SubjectPage_institutiontype")
    inst_migrated = 0
    for row in cursor:
        existing = await db.execute(select(InstitutionType).where(InstitutionType.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        inst = InstitutionType(id=row['id'], name=row['name'])
        db.add(inst)
        inst_migrated += 1

    await db.commit()
    print(f"✓ Migrated {inst_migrated} institution types")

    # Subjects
    print("Migrating subjects...")
    cursor = sqlite_conn.execute("SELECT id, name, code, image_url, hero_image_url FROM SubjectPage_subject")
    subj_migrated = 0
    used_codes = set()

    for row in cursor:
        existing = await db.execute(select(Subject).where(Subject.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        # Handle duplicate subject codes
        code = row['code']
        if code and code in used_codes:
            # Append subject ID to make code unique
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
    print(f"✓ Migrated {subj_migrated} subjects")

    # Subject-InstitutionType relationships
    print("Migrating subject-institution relationships...")
    cursor = sqlite_conn.execute("""
        SELECT subject_id, institutiontype_id
        FROM SubjectPage_subject_institution_type
    """)
    rel_count = 0
    for row in cursor:
        # Get subject with eager loading
        result = await db.execute(
            select(Subject)
            .where(Subject.id == row['subject_id'])
            .options(selectinload(Subject.institution_types))
        )
        subject = result.scalar_one_or_none()

        # Get institution type
        inst = await db.get(InstitutionType, row['institutiontype_id'])

        if subject and inst:
            # Check if relationship already exists
            inst_ids = [it.id for it in subject.institution_types]
            if inst.id not in inst_ids:
                subject.institution_types.append(inst)
                rel_count += 1

    await db.commit()
    print(f"✓ Migrated {rel_count} subject-institution relationships")


async def migrate_templates_and_windows(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate templates and windows"""
    print("Migrating templates...")
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
    print(f"✓ Migrated {templates_migrated} templates")

    # Windows
    print("Migrating windows...")
    cursor = sqlite_conn.execute("""
        SELECT id, template_id, nsub, image_url, image, link, name
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
            image=row['image'],
            link=row['link'],
            name=row['name']
        )
        db.add(window)
        windows_migrated += 1

    await db.commit()
    print(f"✓ Migrated {windows_migrated} windows")


async def migrate_card_topics(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate card topics"""
    print("Migrating card topics...")
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
    print(f"✓ Migrated {topics_migrated} card topics")


async def migrate_cards(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate cards"""
    print("Migrating cards...")
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
            print(f"  Migrated {cards_migrated} cards...")

    await db.commit()
    print(f"✓ Migrated {cards_migrated} cards")

    # Card-Subject relationships
    print("Migrating card-subject relationships...")
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
    print(f"✓ Migrated {rel_count} card-subject relationships")

    # Card-InstitutionType relationships
    print("Migrating card-institution relationships...")
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
    print(f"✓ Migrated {rel_count} card-institution relationships")


async def migrate_tests(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate tests, questions, and answers"""
    print("Migrating tests...")
    cursor = sqlite_conn.execute("""
        SELECT id, title, subject, user_id, duration, difficulty
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
            user_id=row['user_id'],
            duration=row['duration'] if row['duration'] else 30,
            difficulty=row['difficulty'] if row['difficulty'] else 'medium',
        )
        db.add(test)
        tests_migrated += 1

    await db.commit()
    print(f"✓ Migrated {tests_migrated} tests")

    # Questions
    print("Migrating questions...")
    cursor = sqlite_conn.execute("""
        SELECT id, test_id, text, photo, video
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
    print(f"✓ Migrated {questions_migrated} questions")

    # Answers
    print("Migrating answers...")
    cursor = sqlite_conn.execute("""
        SELECT id, question_id, text, is_correct
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
    print(f"✓ Migrated {answers_migrated} answers")


async def migrate_qmj(db: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate QMJ (lesson plans)"""
    print("Migrating QMJ...")
    cursor = sqlite_conn.execute("""
        SELECT id, grade, quarter, code, title, text, hour, "order", file, author_id, created_at, updated_at
        FROM QmjPage_qmj
    """)

    qmj_migrated = 0
    for row in cursor:
        existing = await db.execute(select(QMJ).where(QMJ.id == row['id']))
        if existing.scalar_one_or_none():
            continue

        qmj = QMJ(
            id=row['id'],
            grade=row['grade'],
            quarter=row['quarter'],
            code=row['code'],
            title=row['title'],
            text=row['text'],
            hour=row['hour'] if row['hour'] else 1,
            order=row['order'] if row['order'] else 0,
            file=row['file'],
            author_id=row['author_id'],
        )
        db.add(qmj)
        qmj_migrated += 1

        if qmj_migrated % 500 == 0:
            await db.commit()
            print(f"  Migrated {qmj_migrated} QMJ...")

    await db.commit()
    print(f"✓ Migrated {qmj_migrated} QMJ")

    # QMJ-Subject relationships
    print("Migrating QMJ-subject relationships...")
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
    print(f"✓ Migrated {rel_count} QMJ-subject relationships")

    # QMJ-InstitutionType relationships
    print("Migrating QMJ-institution relationships...")
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
    print(f"✓ Migrated {rel_count} QMJ-institution relationships")


async def main():
    """Main migration function"""
    print("=" * 60)
    print("Data Migration: Django SQLite → FastAPI PostgreSQL")
    print("=" * 60)

    if not SQLITE_DB.exists():
        print(f"Error: SQLite database not found at {SQLITE_DB}")
        return

    sqlite_conn = get_sqlite_connection()
    print(f"Connected to SQLite: {SQLITE_DB}")

    async with async_session_maker() as db:
        print("Connected to PostgreSQL")
        print()

        try:
            # Migrate in order (respecting foreign keys)
            await migrate_users(db, sqlite_conn)
            await migrate_subjects_and_institutions(db, sqlite_conn)
            await migrate_templates_and_windows(db, sqlite_conn)
            await migrate_card_topics(db, sqlite_conn)
            await migrate_cards(db, sqlite_conn)
            await migrate_tests(db, sqlite_conn)
            await migrate_qmj(db, sqlite_conn)

            print()
            print("=" * 60)
            print("✓ Migration completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Error during migration: {e}")
            raise
        finally:
            sqlite_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
