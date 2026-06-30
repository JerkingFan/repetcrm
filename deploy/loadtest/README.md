# Нагрузочное тестирование RepetCRM

Стек: **k6** (Grafana) + seed-скрипт Python в backend-контейнере.

## Быстрый старт на сервере

```bash
cd /opt/repetcrm
git pull

# backend должен быть запущен
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# опционально: свой конфиг
cp deploy/loadtest/.env.loadtest.example deploy/loadtest/.env.loadtest

chmod +x deploy/scripts/loadtest.sh

# smoke (~15 сек) — после каждого деплоя
./deploy/scripts/loadtest.sh smoke

# основной сценарий: 50 репетиторов, 2 мин steady state
./deploy/scripts/loadtest.sh tutor-daily

# стресс: ramp до 100 VU
SCENARIO=stress ./deploy/scripts/loadtest.sh
```

## Что тестируется

| Сценарий | VUs | Длительность | Эндпоинты |
|----------|-----|--------------|-----------|
| `smoke` | 1 | 15s | `/health`, login, `/dashboard` |
| `tutor-daily` | 50 (default) | ~3 min | dashboard, students, lessons, student detail, `/auth/me` |
| `stress` | 25→100 | ~5 min | dashboard, students, lessons (read-heavy) |

Seed создаёт аккаунты `tutor-001@loadtest.local` … `tutor-050@loadtest.local` с паролем из `LOADTEST_PASSWORD`.

## Критерии «зелёного» прогона (tutor-daily)

- `http_req_failed` < **2%**
- `http_req_duration` **p95** < **800 ms**
- `dashboard` p95 < **500 ms**
- `checks` > **95%**

Итог пишется в `deploy/loadtest/results/summary-*.json`.

## Переменные окружения

См. `deploy/loadtest/.env.loadtest.example`:

- `BASE_URL` — URL API (на сервере: `http://127.0.0.1:8000`)
- `TUTORS`, `STUDENTS`, `LESSONS` — объём seed-данных
- `RAMP_UP`, `STEADY`, `RAMP_DOWN` — профиль нагрузки

## Очистка тестовых данных

```bash
./deploy/scripts/loadtest.sh --cleanup
```

Удаляет пользователей `*@loadtest.local` (каскадом — их учеников и уроки).

## Локально (Windows / dev)

```powershell
cd backend
python scripts/seed_loadtest_users.py --count 5 --output ../deploy/loadtest/results/users.json

docker run --rm --network host `
  -v "${PWD}/../deploy/loadtest/k6:/scripts:ro" `
  -v "${PWD}/../deploy/loadtest/results:/results" `
  -v "${PWD}/../deploy/loadtest/results/users.json:/data/users.json:ro" `
  -e BASE_URL=http://127.0.0.1:8000 `
  grafana/k6:0.54.0 run /scripts/smoke.js
```

## Важно

- **Не гоняй stress на проде с реальными пользователями** в часы пик — только staging или ночное окно.
- Login в `tutor-daily` делается один раз в `setup()` (50 последовательных логинов), чтобы не упереться в rate limit.
- AI/PDF/доски в базовый сценарий **не включены** (дорогие внешние вызовы). Добавим отдельным сценарием при необходимости.

## После деплоя (чеклист)

```bash
curl -s http://127.0.0.1:8000/health
./deploy/scripts/loadtest.sh smoke
./deploy/scripts/loadtest.sh tutor-daily
```
