#!/usr/bin/env bash
# Бэкап SQLite-базы RepetCRM
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DB="${ROOT}/backend/data/repetcrm.db"
BACKUP_DIR="${ROOT}/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"

if [[ ! -f "$DB" ]]; then
  echo "База не найдена: $DB"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$DB" "${BACKUP_DIR}/repetcrm_${STAMP}.db"
echo "OK: ${BACKUP_DIR}/repetcrm_${STAMP}.db"
