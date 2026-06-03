# WebSocket доски (виртуальная доска)

## Nginx

Для `wss://домен/api/boards/ws/{id}` обязательны:

- `proxy_http_version 1.1`
- `proxy_set_header Upgrade $http_upgrade`
- `proxy_set_header Connection "upgrade"`
- **`proxy_read_timeout`** и **`proxy_send_timeout`** не меньше длительности урока (в примере `3600s`)

Готовый фрагмент: `deploy/nginx/repetcrm.conf.example` (location `/api/boards/ws/`).

Sticky sessions (ip_hash) **не нужны**: состояние доски в памяти привязано к `board_id`, а не к сокету конкретного воркера.

## Несколько воркеров Uvicorn

In-memory комнаты (`_BoardRoomStore`) и broadcast живут **в одном процессе**. Если запустить `uvicorn --workers 2+` без общего bus:

- клиенты на разных воркерах **не увидят** чужие ops;
- debounced persist может писать разные снимки.

**Продакшен-варианты:**

1. **Один воркер** для API с WebSocket (проще всего для малых и средних нагрузок).
2. **Redis pub/sub** (или аналог): broadcast ops между воркерами + общий store / периодический flush в БД (потребует доработки кода).

Пример запуска с одним воркером:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Keepalive

Клиент шлёт `{ "type": "ping" }` каждые ~25 с; сервер отвечает `{ "type": "pong" }`. Это удерживает соединение за nginx и NAT.
