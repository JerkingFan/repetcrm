# Деплой RepetCRM на сервер

## Что залить на сервер

Минимум (без `node_modules`, `.venv`, моделей):

```
repetcrm/
├── backend/app/
├── backend/requirements-prod.txt
├── backend/Dockerfile.prod
├── frontend/          (исходники, без node_modules)
├── deploy/
├── docker-compose.prod.yml
├── .env.production.example
└── landing/           (опционально)
```

С Windows можно собрать архив:

```powershell
.\scripts\pack-for-server.ps1
```

---

## Вариант 1: Docker (рекомендуется)

### Требования

- Docker 24+ и Docker Compose v2
- 2 ГБ RAM минимум (без локальных нейросетей)
- Открытые порты 3000 (фронт) и 8000 (API) или nginx 80/443

### Шаги

1. Скопируйте проект на сервер, например `/opt/repetcrm`.

2. Создайте конфиг:
   ```bash
   cp .env.production.example .env.production
   nano .env.production
   ```
   Обязательно:
   - `SECRET_KEY` — длинная случайная строка
   - `OPENROUTER_API_KEY` — ключ с https://openrouter.ai
   - `NEXT_PUBLIC_API_URL` — URL API **как в браузере** (например `https://your-domain.com/api`)
   - `CORS_ORIGINS` — URL сайта (например `https://your-domain.com`)

3. **SQLite** (проще):
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
   ```

4. **PostgreSQL** (только после миграции данных — иначе потеряете доступ к аккаунтам):
   ```bash
   # 1. Бэкап (уже делается при SQLITE_BACKUP_ON_STARTUP=true)
   ./deploy/scripts/backup-sqlite.sh

   # 2. Поднять Postgres
   docker compose -f docker-compose.prod.yml --env-file .env.production --profile postgres up -d db

   # 3. Скопировать SQLite → PostgreSQL (сохраняет пароли и id)
   docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend \
     python scripts/migrate_sqlite_to_postgres.py --sqlite /app/data/repetcrm.db \
     --postgres-url "postgresql+psycopg2://USER:PASS@db:5432/repetcrm"

   # 4. В .env.production: DATABASE_URL=postgresql+... и SQLITE_MIGRATION_COMPLETED=true
   docker compose -f docker-compose.prod.yml --env-file .env.production --profile postgres up -d --build

   # 5. Проверка: users_count должен совпасть с числом до миграции
   curl -s http://127.0.0.1:8000/health
   ```

5. Проверка:
   - API: `http://SERVER_IP:8000/docs`
   - CRM: `http://SERVER_IP:3000`

### Nginx + HTTPS

Пример: `deploy/nginx/repetcrm.conf.example`  
После настройки укажите `NEXT_PUBLIC_API_URL=https://ваш-домен/api`.

**Виртуальная доска (WebSocket):** увеличьте `proxy_read_timeout` для `/api/boards/ws/` (см. пример nginx и [deploy/WEBSOCKET.md](WEBSOCKET.md)). Для API с доской рекомендуется **`uvicorn --workers 1`** или Redis pub/sub между воркерами.

---

## Вариант 2: Без Docker (VPS вручную)

### Backend

```bash
cd /opt/repetcrm/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-prod.txt

cp ../.env.production.example .env
nano .env   # DATABASE_URL, SECRET_KEY, OPENROUTER_*

mkdir -p data media
# SQLite: опционально применить deploy/sql/sqlite/01_schema.sql

uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Systemd: `deploy/systemd/repetcrm-backend.service`

### Frontend

```bash
cd /opt/repetcrm/frontend
echo "NEXT_PUBLIC_API_URL=https://api.example.com" > .env.local
npm ci
npm run build
npm run start
```

Systemd: `deploy/systemd/repetcrm-frontend.service`

---

## База данных

| Режим | Когда использовать |
|-------|-------------------|
| SQLite | **Текущий прод по умолчанию** — аккаунты в `backend_data` volume |
| PostgreSQL | После явной миграции `scripts/migrate_sqlite_to_postgres.py` |

**Защита аккаунтов (production):**
- SQLite бэкап **до** Alembic при `SQLITE_BACKUP_ON_STARTUP=true`
- Старт на PostgreSQL **заблокирован**, если в `./data/repetcrm.db` ещё есть пользователи и не задан `SQLITE_MIGRATION_COMPLETED=true`
- Опционально `PRODUCTION_MIN_USERS=N` — отказ старта, если в БД меньше N пользователей

SQL-скрипты: см. [deploy/sql/README.md](sql/README.md).

При первом запуске backend применяет миграции Alembic (`init_db()` → `alembic upgrade head`). Существующие SQLite-базы без `alembic_version` автоматически получают `stamp head` без пересоздания таблиц.

---

## Бэкап SQLite

**Автоматически при старте API** (рекомендуется на проде):

```env
# .env.production
SQLITE_BACKUP_ON_STARTUP=true
SQLITE_BACKUP_DIR=./backups
SQLITE_BACKUP_KEEP=14
```

Бэкапы лежат в volume `backend_data` → `/app/backups` внутри контейнера (или рядом с `data/`).

**Вручную:**

```bash
./deploy/scripts/backup-sqlite.sh
```

**Cron (ежедневно в 3:00):**

```bash
0 3 * * * cd /opt/repetcrm && ./deploy/scripts/backup-sqlite.sh >> /var/log/repetcrm-backup.log 2>&1
```

**Проверка после деплоя:**

```bash
curl -s http://127.0.0.1:8000/health
# database.users_count должен совпадать с ожидаемым числом юзеров
```

Копирует `backend/data/repetcrm.db` в `backups/` с датой.

---

## Чеклист перед открытием пользователям

- [ ] `DATABASE_URL=sqlite:///./data/repetcrm.db` (если не мигрировали на Postgres)
- [ ] `SQLITE_BACKUP_ON_STARTUP=true`
- [ ] `curl /health` → `database.users_count` > 0
- [ ] `OPENROUTER_API_KEY` задан, `HOMEWORK_AI_PROVIDER=openrouter`
- [ ] `CORS_ORIGINS` = ваш домен
- [ ] `NEXT_PUBLIC_API_URL` совпадает с тем, что видит браузер
- [ ] Порты 8000/3000 открыты или настроен nginx
- [ ] Тома `data/` и `media/` на persistent volume (Docker volumes или каталог на диске)

---

## Обновление версии

```bash
cd /opt/repetcrm
git pull   # или залить новый архив
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
./deploy/scripts/loadtest.sh smoke   # быстрая проверка после деплоя
```

Стек поднимает **3 backend-процесса**: API (`backend`), фоновый worker (`worker`), Redis.

Проверка worker:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f worker
# ожидайте: "Starting worker" и "ARQ pool connected" при генерации ДЗ
```

Без Redis jobs выполняются внутри API-процесса (как раньше). С Redis + worker — AI/PDF не блокируют API и переживают рестарт API.

Подробнее: [deploy/loadtest/README.md](loadtest/README.md).

### Метрики и логи

- **Логи:** в production JSON в stdout (`LOG_FORMAT=auto`). Смотреть: `docker compose logs -f backend`.
- **Prometheus:** `GET /metrics` — `http_requests_total`, `http_request_duration_seconds`, `repetcrm_users_total`, `repetcrm_redis_up`.
- В production задайте `METRICS_TOKEN` и ограничьте `/metrics` в nginx (внутренняя сеть или Bearer).

```bash
curl -s -H "Authorization: Bearer YOUR_METRICS_TOKEN" http://127.0.0.1:8000/metrics
```

### Sentry

- Backend: `SENTRY_DSN` в `.env.production` (опционально).
- Frontend: `NEXT_PUBLIC_SENTRY_DSN` при сборке (`frontend/.env.local` или build args).

### Доска: снимки состояния

При автосохранении доски пишется snapshot в `board_snapshots` (последние `BOARD_SNAPSHOT_KEEP=20` на доску) — для восстановления после сбоя.

### Доска: guest read-only

- Новые доски: ученик по ссылке **только смотрит** (`share_writable=false`).
- Существующие доски после миграции: **рисование по ссылке сохранено** (`share_writable=true`).
- Владелец включает «Ученик может рисовать» на странице доски.

### Rate limit и Redis

- API: `API_RATE_LIMIT_MAX=120` запросов / `API_RATE_LIMIT_WINDOW_SEC=60` на IP (кроме `/health`, `/metrics`, WebSocket).
- Redis в Docker: задайте `REDIS_PASSWORD` и обновите `REDIS_URL=redis://:password@redis:6379/0`.
- Nginx: `limit_req` в `deploy/nginx/repetcrm.conf.example`.

При изменении схемы БД — `deploy/sql/migrations/`.
