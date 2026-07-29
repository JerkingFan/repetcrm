#!/usr/bin/env bash
# PostgreSQL backup for RepetCRM (Docker Compose prod or native pg_dump)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${ROOT}/backups/postgres}"
STAMP="$(date +%Y%m%d_%H%M%S)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT}/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.production}"

mkdir -p "$BACKUP_DIR"

if [[ -f "$COMPOSE_FILE" ]] && [[ -f "$ENV_FILE" ]] && docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q db 2>/dev/null | grep -q .; then
  # Docker Compose: dump via exec into postgres container
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  PGUSER="${POSTGRES_USER:-repetcrm}"
  PGDB="${POSTGRES_DB:-repetcrm}"
  OUT="${BACKUP_DIR}/repetcrm_pg_${STAMP}.sql.gz"
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
    pg_dump -U "$PGUSER" -d "$PGDB" --no-owner --no-acl | gzip -9 > "$OUT"
  echo "OK: $OUT"
  exit 0
fi

# Native pg_dump (DATABASE_URL or PG* env)
if [[ -n "${DATABASE_URL:-}" ]]; then
  OUT="${BACKUP_DIR}/repetcrm_pg_${STAMP}.sql.gz"
  pg_dump "$DATABASE_URL" --no-owner --no-acl | gzip -9 > "$OUT"
  echo "OK: $OUT"
  exit 0
fi

echo "PostgreSQL not found: start db service or set DATABASE_URL"
exit 1
