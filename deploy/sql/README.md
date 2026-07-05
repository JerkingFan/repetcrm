# SQL-скрипты RepetCRM

## Таблицы

| Таблица | Описание |
|---------|----------|
| `users` | Репетиторы (логин) |
| `students` | Ученики |
| `lessons` | Занятия |
| `checklist_items` | Чек-лист тем на уроке |
| `homeworks` | Домашние задания |

## PostgreSQL (рекомендуется на сервере)

```bash
# Создать пользователя и БД (один раз)
sudo -u postgres psql -c "CREATE USER repetcrm WITH PASSWORD 'your-password';"
sudo -u postgres psql -c "CREATE DATABASE repetcrm OWNER repetcrm;"

# Применить схему
psql -U repetcrm -d repetcrm -f deploy/sql/postgresql/01_schema.sql

# Миграция со старой версии (если БД уже была)
psql -U repetcrm -d repetcrm -f deploy/sql/migrations/postgresql/001_legacy_columns.sql
```

Через Docker (профиль `postgres` в `docker-compose.prod.yml`) схема подтянется из `deploy/sql/postgresql/` при первом запуске контейнера.

`DATABASE_URL`:
```
postgresql+psycopg2://repetcrm:PASSWORD@localhost:5432/repetcrm
```

## SQLite (проще, один файл)

```bash
mkdir -p backend/data
sqlite3 backend/data/repetcrm.db < deploy/sql/sqlite/01_schema.sql
```

Или приложение применит миграции Alembic при старте (`init_db()` → `alembic upgrade head`).

`DATABASE_URL`:
```
sqlite:///./data/repetcrm.db
```

## Миграции

**Основной способ (с версии с Alembic):** `backend/alembic/versions/` — миграции применяются автоматически при старте API и worker.

```bash
cd backend
# вручную:
DATABASE_URL=sqlite:///./data/repetcrm.db python -m alembic upgrade head
# существующая БД без alembic_version (обновление со старой версии):
DATABASE_URL=... python -m alembic stamp head
```

Папка `deploy/sql/migrations/` — **устаревшие** SQL-скрипты для ручного обновления без Alembic (архив).
На чистом сервере достаточно `01_schema.sql`.
