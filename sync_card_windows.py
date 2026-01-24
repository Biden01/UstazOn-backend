"""
Синхронный скрипт для обновления window_id у Cards
"""
import sqlite3
import psycopg2

# Подключения
OLD_DB = "/tmp/old_db.sqlite3"  # Will be copied to container
NEW_DB_PARAMS = {
    'dbname': 'ustazon',
    'user': 'postgres',
    'password': 'postgres',
    'host': 'db',  # Docker service name
    'port': '5432'
}

def main():
    # Подключаемся к старой базе
    old_conn = sqlite3.connect(OLD_DB)
    old_cursor = old_conn.cursor()

    # Подключаемся к новой базе
    new_conn = psycopg2.connect(**NEW_DB_PARAMS)
    new_cursor = new_conn.cursor()

    print("=" * 80)
    print("🔄 ОБНОВЛЕНИЕ window_id У CARDS")
    print("=" * 80)

    # Получаем связи card name -> window_id из старой базы
    print("\n📋 Получение связей из старой базы...")
    old_cursor.execute("""
        SELECT DISTINCT
            c.name as card_name,
            w.id as window_id,
            w.name as window_name
        FROM MaterialsPage_card c
        JOIN TemplatesPage_window w ON c.window_id = w.id
    """)

    card_window_map = {}  # card_name -> window_id
    for card_name, window_id, window_name in old_cursor.fetchall():
        card_window_map[card_name] = (window_id, window_name)

    print(f"✅ Найдено {len(card_window_map)} уникальных связей card->window")

    # Обновляем cards в новой базе
    print("\n📋 Обновление Cards...")
    updated_count = 0
    not_found = 0

    for card_name, (window_id, window_name) in card_window_map.items():
        # Проверяем, существует ли карточка в новой базе
        new_cursor.execute("SELECT id, window_id FROM cards WHERE name = %s LIMIT 1", (card_name,))
        result = new_cursor.fetchone()

        if result:
            card_id, current_window_id = result

            if current_window_id is None:
                # Обновляем только если window_id еще не установлен
                new_cursor.execute(
                    "UPDATE cards SET window_id = %s WHERE id = %s",
                    (window_id, card_id)
                )
                updated_count += 1
                if updated_count <= 10:  # Показываем только первые 10
                    print(f"  ✅ '{card_name[:50]}...' -> Window '{window_name}' (id={window_id})")
        else:
            not_found += 1

    new_conn.commit()

    print(f"\n✅ Обновлено Cards: {updated_count}")
    print(f"⚠️  Не найдено в новой базе: {not_found}")

    # Связываем Subjects с Windows
    print("\n📋 Связывание Subjects с Windows...")

    # Получаем связи subject code -> window_ids из старой базы
    old_cursor.execute("""
        SELECT DISTINCT
            s.code as subject_code,
            w.id as window_id,
            w.name as window_name
        FROM MaterialsPage_card_subject cs
        JOIN MaterialsPage_card c ON cs.card_id = c.id
        JOIN SubjectPage_subject s ON cs.subject_id = s.id
        JOIN TemplatesPage_window w ON c.window_id = w.id
        WHERE s.code IS NOT NULL
    """)

    subject_windows = {}  # subject_code -> set of window_ids
    for subject_code, window_id, window_name in old_cursor.fetchall():
        if subject_code not in subject_windows:
            subject_windows[subject_code] = set()
        subject_windows[subject_code].add((window_id, window_name))

    print(f"✅ Найдено {len(subject_windows)} subjects со связями к windows")

    # Связываем в новой базе
    subjects_linked = 0
    links_created = 0

    for subject_code, windows in subject_windows.items():
        # Находим subject в новой базе
        new_cursor.execute("SELECT id FROM subjects WHERE code = %s", (subject_code,))
        result = new_cursor.fetchone()

        if result:
            subject_id = result[0]

            for window_id, window_name in windows:
                # Проверяем, есть ли уже связь
                new_cursor.execute(
                    "SELECT 1 FROM subject_window WHERE subject_id = %s AND window_id = %s",
                    (subject_id, window_id)
                )

                if not new_cursor.fetchone():
                    # Создаем связь
                    new_cursor.execute(
                        "INSERT INTO subject_window (subject_id, window_id) VALUES (%s, %s)",
                        (subject_id, window_id)
                    )
                    links_created += 1

                    if links_created <= 10:
                        print(f"  🔗 Subject '{subject_code}' <-> Window '{window_name}'")

            subjects_linked += 1

    new_conn.commit()

    print(f"\n✅ Subjects связано: {subjects_linked}")
    print(f"✅ Связей создано: {links_created}")

    print("\n" + "=" * 80)
    print("🎉 ОБНОВЛЕНИЕ ЗАВЕРШЕНО!")
    print("=" * 80)
    print(f"  📌 Cards обновлено: {updated_count}")
    print(f"  🔗 Subject-Window связей: {links_created}")
    print("=" * 80)

    # Закрываем соединения
    old_conn.close()
    new_cursor.close()
    new_conn.close()


if __name__ == "__main__":
    main()
