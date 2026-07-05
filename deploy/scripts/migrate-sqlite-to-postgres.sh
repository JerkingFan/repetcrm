#!/usr/bin/env bash
# Migrate SQLite accounts to PostgreSQL (run from repo root).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.production}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy from .env.production.example" >&2
  exit 1
fi

# shellcheck disable=SC1090
source <(grep -E '^(POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_DB|DATABASE_URL)=' "$ENV_FILE" | sed 's/^/export /')

PG_USER="${POSTGRES_USER:-repetcrm}"
PG_PASS="${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in $ENV_FILE}"
PG_DB="${POSTGRES_DB:-repetcrm}"
PG_URL="${DATABASE_URL:-postgresql+psycopg2://${PG_USER}:${PG_PASS}@db:5432/${PG_DB}}"

echo "Starting Postgres profile..."
docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE" --profile postgres up -d db

echo "Migrating /app/data/repetcrm.db → PostgreSQL..."
docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE" --profile postgres run --rm backend \
  python scripts/migrate_sqlite_to_postgres.py \
  --sqlite /app/data/repetcrm.db \
  --postgres-url "$PG_URL"

echo "Done. Set DATABASE_URL and SQLITE_MIGRATION_COMPLETED=true in $ENV_FILE, then redeploy."
