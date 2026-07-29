# WebSocket доски (виртуальная доска)

## Nginx

Для `wss://домен/api/boards/ws/{id}` обязательны:

- `proxy_http_version 1.1`
- `proxy_set_header Upgrade $http_upgrade`
- `proxy_set_header Connection "upgrade"`
- **`proxy_read_timeout`** и **`proxy_send_timeout`** не меньше длительности урока (в примере `3600s`)

Готовый фрагмент: `deploy/nginx/repetcrm.conf.example` (location `/api/boards/ws/`).

Sticky sessions (ip_hash) **не нужны** при включённом Redis board bus.

## Несколько воркеров Uvicorn

С **REDIS_URL** и `board_bus` (см. `app/services/board_bus.py`):

- ops рассылаются через Redis pub/sub между процессами API;
- debounced persist остаётся на воркере, принявшем op от клиента;
- можно поднять `uvicorn --workers 2+` (осторожно с in-memory job queue — ARQ worker отдельно).

Без Redis — только **один воркер** для WebSocket:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Проверка: `GET /health` → `"board_bus": "redis"`.

## Keepalive

Клиент шлёт `{ "type": "ping" }` каждые ~25 с; сервер отвечает `{ "type": "pong" }`. Это удерживает соединение за nginx и NAT.

## Auth (JWT и guest share token)

Рекомендация: не передавать токены в query string, чтобы они не попадали в access logs.

### Tutor (аутентифицированный репетитор)

- Клиентский браузер автоматически пришлёт cookie `repetcrm_access` на handshake.
- Для non-browser клиентов (script/curl) поддерживается `Authorization: Bearer <jwt>` заголовок.

Поддерживаемый URL: `wss://<domain>/api/boards/ws/{id}` (без `?auth=...`).

### Guest (доступ по ссылке)

- Guest-режим использует cookie `repetcrm_board_share=<share_token>` (ставится клиентом перед подключением).
- Подключение идёт на URL без query string: `wss://<domain>/api/boards/ws/{id}`.

### Legacy (переходный период)

Сервер продолжает принимать `?auth=...` (JWT) и `?token=...` (guest share token) как fallback, но пишет warning в логах. Планируется удаление.
