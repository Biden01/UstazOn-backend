#!/usr/bin/env python3
"""
Главный скрипт миграции всех данных из Django SQLite в FastAPI PostgreSQL
Запускает все миграции в правильном порядке с учетом внешних ключей
"""
import asyncio
import subprocess
import sys
from pathlib import Path


async def run_migration_script(script_name: str) -> bool:
    """Запуск одного скрипта миграции"""
    print(f"\n{'='*60}")
    print(f"Запуск: {script_name}")
    print('='*60)

    script_path = Path(__file__).parent / script_name

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✓ {script_name} завершен успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Ошибка в {script_name}: {e}")
        return False


async def main():
    """Главная функция - запускает все миграции по порядку"""
    print("="*60)
    print("ПОЛНАЯ МИГРАЦИЯ ДАННЫХ")
    print("Django SQLite → FastAPI PostgreSQL")
    print("="*60)

    # Порядок миграций важен из-за внешних ключей!
    migration_scripts = [
        "migrate_users.py",           # 1. Пользователи (для author_id)
        "migrate_subjects.py",        # 2. Предметы и типы учреждений
        "migrate_templates.py",       # 3. Шаблоны и окна (для window_id)
        "migrate_cards.py",           # 4. Карточки и темы
        "migrate_qmj.py",             # 5. ҚМЖ (календарные планы)
        "migrate_tests.py",           # 6. Тесты, вопросы, ответы
    ]

    success_count = 0
    failed_scripts = []

    for script in migration_scripts:
        success = await run_migration_script(script)
        if success:
            success_count += 1
        else:
            failed_scripts.append(script)
            # Продолжаем несмотря на ошибку, чтобы увидеть все проблемы
            print(f"\n⚠️  Продолжение после ошибки в {script}...\n")

    # Итоговый отчет
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    print(f"Успешно выполнено: {success_count}/{len(migration_scripts)}")

    if failed_scripts:
        print(f"\n❌ Ошибки в следующих скриптах:")
        for script in failed_scripts:
            print(f"  - {script}")
        sys.exit(1)
    else:
        print("\n✓ ВСЕ МИГРАЦИИ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
