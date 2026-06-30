#!/usr/bin/env bash
# Деплой RepetCRM с GitHub: первый запуск или обновление.
# Использование:
#   curl -fsSL .../deploy/scripts/deploy.sh | bash          # не рекомендуется без проверки
#   ./deploy/scripts/deploy.sh                              # из клона репозитория
#   INSTALL_DIR=/opt/repetcrm ./deploy/scripts/deploy.sh    # первый клон в /opt/repetcrm

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/JerkingFan/repetcrm.git}"
INSTALL_DIR="${INSTALL_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
PROFILE="${PROFILE:-}" # postgres — для PostgreSQL: PROFILE=postgres ./deploy.sh

if ! command -v docker >/dev/null 2>&1; then
  echo "Ошибка: Docker не установлен. Установите Docker 24+ и Docker Compose v2."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Ошибка: docker compose (v2) не найден."
  exit 1
fi

if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo "Клонирую $REPO_URL → $INSTALL_DIR"
  sudo mkdir -p "$(dirname "$INSTALL_DIR")"
  sudo git clone "$REPO_URL" "$INSTALL_DIR"
  sudo chown -R "$USER:$USER" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [ -d .git ]; then
  echo "git pull..."
  git pull --ff-only
fi

if [ ! -f "$ENV_FILE" ]; then
  cp .env.production.example "$ENV_FILE"
  echo ""
  echo "Создан $ENV_FILE — отредактируйте перед запуском:"
  echo "  nano $INSTALL_DIR/$ENV_FILE"
  echo ""
  echo "Обязательно:"
  echo "  SECRET_KEY          — случайная строка 32+ символов"
  echo "  OPENROUTER_API_KEY  — ключ с https://openrouter.ai"
  echo "  NEXT_PUBLIC_API_URL — URL API в браузере (например https://repetcrm.ru/api)"
  echo "  CORS_ORIGINS        — URL сайта (например https://repetcrm.ru)"
  echo ""
  echo "Затем снова: ./deploy/scripts/deploy.sh"
  exit 0
fi

COMPOSE_ARGS=(-f "$COMPOSE_FILE" --env-file "$ENV_FILE")
if [ -n "$PROFILE" ]; then
  COMPOSE_ARGS+=(--profile "$PROFILE")
fi

echo "Сборка и запуск контейнеров..."
docker compose "${COMPOSE_ARGS[@]}" up -d --build

echo ""
echo "Готово."
echo "  API:      http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000/docs"
echo "  Frontend: http://$(hostname -I 2>/dev/null | awk '{print $1}'):3000"
echo ""
echo "Логи: docker compose ${COMPOSE_ARGS[*]} logs -f"
