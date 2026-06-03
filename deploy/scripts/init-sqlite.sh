#!/usr/bin/env bash
# Инициализация SQLite на сервере
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DB="${ROOT}/backend/data/repetcrm.db"
mkdir -p "$(dirname "$DB")"
sqlite3 "$DB" < "${ROOT}/deploy/sql/sqlite/01_schema.sql"
echo "OK: $DB"
