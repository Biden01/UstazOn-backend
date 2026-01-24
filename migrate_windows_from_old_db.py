"""
Скрипт для переноса данных Window из старой Django SQLite базы в новую PostgreSQL
"""
import asyncio
import sqlite3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.models import Subject, Window, Card, Template
from src.db.base import Base


# Путь к старой SQLite базе
OLD_DB_PATH = "/Users/erasylbidan/UstazOn/backend_old/UstazOn/db.sqlite3"

# Новая PostgreSQL база (из .env)
NEW_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ustazon"


async def migrate_windows():
    """Переносим Window из старой Django базы в новую PostgreSQL"""

    # Подключаемся к старой SQLite базе
    old_conn = sqlite3.connect(OLD_DB_PATH)
    old_cursor = old_conn.cursor()

    # Подключаемся к новой PostgreSQL базе
    engine = create_async_engine(NEW_DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("=" * 80)
        print("🔄 МИГРАЦИЯ WINDOW ИЗ СТАРОЙ БАЗЫ")
        print("=" * 80)

        # 1. Переносим Templates
        print("\n📋 Шаг 1: Перенос Templates")
        old_cursor.execute("SELECT id, name, code_name FROM TemplatesPage_template")
        templates_map = {}  # old_id -> new_id

        for old_id, name, code_name in old_cursor.fetchall():
            # Проверяем, есть ли уже такой template
            result = await session.execute(
                select(Template).where(Template.code_name == code_name)
            )
            template = result.scalar_one_or_none()

            if not template:
                template = Template(
                    name=name,
                    code_name=code_name
                )
                session.add(template)
                await session.flush()
                print(f"  ✅ Создан template: {name} (old_id={old_id}, new_id={template.id})")
            else:
                print(f"  ℹ️  Template уже существует: {name} (old_id={old_id}, new_id={template.id})")

            templates_map[old_id] = template.id

        await session.commit()
        print(f"\n✅ Перенесено Templates: {len(templates_map)}")

        # 2. Переносим Windows
        print("\n📋 Шаг 2: Перенос Windows")
        old_cursor.execute("""
            SELECT id, name, template_id, link, nsub, image_url
            FROM TemplatesPage_window
        """)

        windows_map = {}  # old_id -> new Window object

        for old_id, name, template_id, link, nsub, image_url in old_cursor.fetchall():
            # Проверяем, есть ли уже такой window
            result = await session.execute(
                select(Window).where(Window.name == name)
            )
            window = result.scalar_one_or_none()

            if not window:
                new_template_id = templates_map.get(template_id) if template_id else None

                window = Window(
                    name=name,
                    template_id=new_template_id,
                    link=link if link else None,
                    nsub=bool(nsub),
                    image_url=image_url if image_url else None
                )
                session.add(window)
                await session.flush()
                print(f"  ✅ Создан window: {name} (old_id={old_id}, new_id={window.id})")
            else:
                print(f"  ℹ️  Window уже существует: {name} (old_id={old_id}, new_id={window.id})")

            windows_map[old_id] = window

        await session.commit()
        print(f"\n✅ Перенесено Windows: {len(windows_map)}")

        # 3. Обновляем Cards - привязываем к Window
        print("\n📋 Шаг 3: Привязка Cards к Windows")
        old_cursor.execute("""
            SELECT id, name, window_id
            FROM MaterialsPage_card
            WHERE window_id IS NOT NULL
        """)

        cards_updated = 0
        for old_card_id, card_name, old_window_id in old_cursor.fetchall():
            if old_window_id not in windows_map:
                print(f"  ⚠️  Window с old_id={old_window_id} не найден для card '{card_name[:50]}'")
                continue

            new_window = windows_map[old_window_id]

            # Находим карточку в новой базе по имени
            result = await session.execute(
                select(Card).where(Card.name == card_name).limit(1)
            )
            card = result.scalar_one_or_none()

            if card:
                card.window_id = new_window.id
                cards_updated += 1
                print(f"  📌 Card '{card_name[:50]}' -> Window '{new_window.name}'")
            else:
                print(f"  ⚠️  Card '{card_name[:50]}' не найдена в новой базе")

        await session.commit()
        print(f"\n✅ Обновлено Cards: {cards_updated}")

        # 4. Связываем Subjects с Windows через MaterialsPage_card
        print("\n📋 Шаг 4: Связывание Subjects с Windows")

        # Получаем все связи subject -> card -> window из старой базы
        old_cursor.execute("""
            SELECT DISTINCT s.code, w.id as window_id, w.name as window_name
            FROM MaterialsPage_card_subject cs
            JOIN MaterialsPage_card c ON cs.card_id = c.id
            JOIN SubjectPage_subject s ON cs.subject_id = s.id
            JOIN TemplatesPage_window w ON c.window_id = w.id
        """)

        subject_window_links = {}  # subject_code -> set of new_window_ids
        for subject_code, old_window_id, window_name in old_cursor.fetchall():
            if subject_code not in subject_window_links:
                subject_window_links[subject_code] = set()

            if old_window_id in windows_map:
                new_window = windows_map[old_window_id]
                subject_window_links[subject_code].add(new_window.id)

        # Привязываем в новой базе
        subjects_updated = 0
        for subject_code, window_ids in subject_window_links.items():
            result = await session.execute(
                select(Subject).where(Subject.code == subject_code)
            )
            subject = result.scalar_one_or_none()

            if subject:
                # Получаем Window объекты
                result = await session.execute(
                    select(Window).where(Window.id.in_(window_ids))
                )
                windows = list(result.scalars().all())

                # Добавляем только новые связи
                existing_window_ids = {w.id for w in subject.windows}
                new_windows = [w for w in windows if w.id not in existing_window_ids]

                if new_windows:
                    subject.windows.extend(new_windows)
                    subjects_updated += 1
                    window_names = [w.name for w in new_windows]
                    print(f"  🔗 Subject '{subject.name}' связан с: {', '.join(window_names)}")
            else:
                print(f"  ⚠️  Subject с кодом '{subject_code}' не найден в новой базе")

        await session.commit()
        print(f"\n✅ Обновлено Subjects: {subjects_updated}")

        print("\n" + "=" * 80)
        print("🎉 МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 80)
        print(f"  📋 Templates: {len(templates_map)}")
        print(f"  🪟 Windows: {len(windows_map)}")
        print(f"  📌 Cards: {cards_updated}")
        print(f"  📚 Subjects: {subjects_updated}")
        print("=" * 80)

    old_conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_windows())
