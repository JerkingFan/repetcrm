#!/usr/bin/env bash
# Безопасный деплой RepetCRM (Docker Compose).
# Запуск на сервере из корня репозитория:
#   ./deploy/scripts/deploy-prod.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.production)
ENV_FILE="$ROOT/.env.production"
VOLUME_NAME="${COMPOSE_PROJECT_NAME:-repetcrm}_backend_data"

red() { printf '\033[31m%s\033[0m\n' "$*"; }
grn() { printf '\033[32m%s\033[0m\n' "$*"; }
ylw() { printf '\033[33m%s\033[0m\n' "$*"; }

if [[ ! -f "$ENV_FILE" ]]; then
  red "Нет .env.production — скопируйте: cp .env.production.example .env.production"
  exit 1
fi

if ! command -v docker >/dev/null; then
  red "Docker не установлен"
  exit 1
fi

# --- проверка критичных переменных ---
require_env() {
  local key="$1"
  if ! grep -q "^${key}=" "$ENV_FILE"; then
    red "В .env.production нет ${key}"
    exit 1
  fi
  local val
  val="$(grep "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' \"')"
  if [[ -z "$val" || "$val" == *"example.com"* || "$val" == *"changeme"* || "$val" == *"сгенерируйте"* ]]; then
    red "Заполните ${key} в .env.production (сейчас: пусто или placeholder)"
    exit 1
  fi
}

require_env SECRET_KEY
require_env NEXT_PUBLIC_API_URL
require_env OPENROUTER_API_KEY

DB_URL="$(grep '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' \"' || true)"
if [[ -z "$DB_URL" ]]; then
  ylw "DATABASE_URL не задан — будет SQLite (sqlite:///./data/repetcrm.db)"
fi
if [[ "$DB_URL" == postgresql* ]]; then
  ylw "Внимание: DATABASE_URL=PostgreSQL. Убедитесь, что данные мигрированы из SQLite volume!"
fi

# --- бэкап SQLite из Docker volume перед обновлением ---
if docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
  ylw "Проверяем пользователей в volume ${VOLUME_NAME}..."
  docker run --rm -v "${VOLUME_NAME}:/data" alpine sh -c '
    apk add --no-cache sqlite >/dev/null 2>&1 || true
    if [ -f /data/repetcrm.db ]; then
      echo "=== users in SQLite ==="
      sqlite3 /data/repetcrm.db "SELECT id, email FROM users;" || true
      mkdir -p /data/backups
      cp /data/repetcrm.db "/data/backups/pre_deploy_$(date +%Y%m%d_%H%M%S).db"
      echo "Backup: /data/backups/pre_deploy_*.db"
    else
      echo "WARN: /data/repetcrm.db not found in volume"
    fi
  '
else
  ylw "Volume ${VOLUME_NAME} ещё не создан — первый деплой"
fi

ylw "Сборка и запуск контейнеров..."
"${COMPOSE[@]}" up -d --build

ylw "Ожидание health backend..."
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT:-8000}/health" >/tmp/repetcrm_health.json 2>/dev/null; then
    break
  fi
  sleep 2
done

if [[ ! -f /tmp/repetcrm_health.json ]]; then
  red "Backend не отвечает на :${BACKEND_PORT:-8000}/health"
  "${COMPOSE[@]}" logs --tail=80 backend
  exit 1
fi

echo ""
grn "=== /health ==="
cat /tmp/repetcrm_health.json
echo ""

USERS="$(python3 -c "import json; d=json.load(open('/tmp/repetcrm_health.json')); print(d.get('database',{}).get('users_count','?'))" 2>/dev/null || echo "?")"
if [[ "$USERS" == "0" ]]; then
  red "ОПАСНО: users_count=0 — API подключён к пустой БД!"
  red "Проверьте DATABASE_URL и volume backend_data. НЕ открывайте пользователям."
  exit 1
fi

grn "users_count=${USERS}"

ylw "Статус контейнеров:"
"${COMPOSE[@]}" ps

grn "Готово. Проверьте в браузере: вход и генерация ДЗ."
grn "Логи: ${COMPOSE[*]} logs -f backend worker"
