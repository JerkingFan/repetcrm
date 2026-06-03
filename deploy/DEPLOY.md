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

4. **PostgreSQL** (надёжнее):
   ```bash
   # В .env.production задайте POSTGRES_PASSWORD и DATABASE_URL=postgresql+psycopg2://...
   docker compose -f docker-compose.prod.yml --env-file .env.production --profile postgres up -d --build
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
| SQLite | Мало пользователей, один сервер, быстрый старт |
| PostgreSQL | Продакшен, бэкапы, рост данных |

SQL-скрипты: см. [deploy/sql/README.md](sql/README.md).

При первом запуске backend также вызывает `init_db()` (создаёт таблицы через SQLAlchemy).

---

## Бэкап SQLite

```bash
./deploy/scripts/backup-sqlite.sh
```

Копирует `backend/data/repetcrm.db` в `backups/` с датой.

---

## Чеклист перед открытием пользователям

- [ ] `SECRET_KEY` изменён
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
```

При изменении схемы БД — `deploy/sql/migrations/`.
