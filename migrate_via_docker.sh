#!/bin/bash

# Скрипт для миграции данных через Docker

# Копируем старую SQLite базу в Docker контейнер
docker cp /Users/erasylbidan/UstazOn/backend_old/UstazOn/db.sqlite3 ustazon_backend:/tmp/old_db.sqlite3

# Копируем скрипт миграции
docker cp /Users/erasylbidan/UstazOn/backend/migrate_windows_from_old_db.py ustazon_backend:/app/migrate.py

# Обновляем путь к старой базе в скрипте
docker exec ustazon_backend sed -i 's|/Users/erasylbidan/UstazOn/backend_old/UstazOn/db.sqlite3|/tmp/old_db.sqlite3|g' /app/migrate.py

# Обновляем DATABASE_URL для подключения к базе через Docker network
docker exec ustazon_backend sed -i 's|localhost:5432|db:5432|g' /app/migrate.py

# Запускаем миграцию
docker exec ustazon_backend python /app/migrate.py
