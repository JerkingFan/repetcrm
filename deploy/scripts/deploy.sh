#!/usr/bin/env bash
# Деплой RepetCRM с GitHub: первый запуск или обновление.
# Использование:
#   ./deploy/scripts/deploy.sh                              # из клона репозитория
#   INSTALL_DIR=/opt/repetcrm ./deploy/scripts/deploy.sh    # первый клон в /opt/repetcrm
#
# После заполнения .env.production делегирует в deploy-prod.sh (проверки + бэкап).

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/JerkingFan/repetcrm.git}"
INSTALL_DIR="${INSTALL_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
ENV_FILE=".env.production"

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
  echo "  FRONTEND_PUBLIC_URL — https://repetcrm.ru"
  echo "  CORS_ORIGINS        — https://repetcrm.ru,https://www.repetcrm.ru"
  echo "  REDIS_PASSWORD + REDIS_URL — один и тот же пароль"
  echo ""
  echo "Затем снова: ./deploy/scripts/deploy.sh"
  echo ""
  echo "Важно: вход/кабинет работают только по HTTPS (COOKIE_SECURE=true)."
  echo "Не проверяйте auth на http://IP:3000 — cookies не сохранятся."
  exit 0
fi

if [ -n "${PROFILE:-}" ]; then
  echo "PROFILE=$PROFILE — запускайте вручную:"
  echo "  docker compose -f docker-compose.prod.yml --env-file .env.production --profile $PROFILE up -d --build"
  exit 1
fi

exec "$(dirname "$0")/deploy-prod.sh"
