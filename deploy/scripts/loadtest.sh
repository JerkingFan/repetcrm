#!/usr/bin/env bash
# RepetCRM load test runner (k6 + seed data).
#
# Usage:
#   ./deploy/scripts/loadtest.sh              # default: tutor-daily, 50 tutors
#   ./deploy/scripts/loadtest.sh smoke      # quick post-deploy check (~15s)
#   SCENARIO=stress ./deploy/scripts/loadtest.sh
#   ./deploy/scripts/loadtest.sh --cleanup    # remove loadtest users
#
# Config: deploy/loadtest/.env.loadtest (optional)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-deploy/loadtest/.env.loadtest}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TUTORS="${TUTORS:-50}"
STUDENTS="${STUDENTS:-10}"
LESSONS="${LESSONS:-20}"
LOADTEST_PASSWORD="${LOADTEST_PASSWORD:-LoadTest123!}"
SCENARIO="${SCENARIO:-tutor-daily}"
K6_IMAGE="${K6_IMAGE:-grafana/k6:0.54.0}"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.production)
RESULTS_DIR="$ROOT/deploy/loadtest/results"
USERS_JSON="$RESULTS_DIR/users.json"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$RESULTS_DIR"

if [[ "${1:-}" == "--cleanup" ]]; then
  echo "==> Removing loadtest users (*@${LOADTEST_EMAIL_DOMAIN:-loadtest.local})..."
  "${COMPOSE[@]}" exec -T backend python scripts/seed_loadtest_users.py \
    --count "$TUTORS" --cleanup
  rm -f "$USERS_JSON"
  echo "Done."
  exit 0
fi

if [[ -n "${1:-}" ]]; then
  SCENARIO="$1"
fi

case "$SCENARIO" in
  smoke|tutor-daily|stress) ;;
  *)
    echo "Unknown scenario: $SCENARIO (use smoke | tutor-daily | stress)"
    exit 1
    ;;
esac

# smoke needs minimal data
SEED_TUTORS="$TUTORS"
SEED_STUDENTS="$STUDENTS"
SEED_LESSONS="$LESSONS"
if [[ "$SCENARIO" == "smoke" ]]; then
  SEED_TUTORS=1
  SEED_STUDENTS=2
  SEED_LESSONS=3
fi

echo "==> Health check: $BASE_URL/health"
if ! curl -sf "$BASE_URL/health" >/dev/null; then
  echo "Backend not reachable at $BASE_URL — start stack first."
  exit 1
fi

echo "==> Seeding $SEED_TUTORS tutors × $SEED_STUDENTS students × $SEED_LESSONS lessons..."
"${COMPOSE[@]}" exec -T backend python scripts/seed_loadtest_users.py \
  --count "$SEED_TUTORS" \
  --students "$SEED_STUDENTS" \
  --lessons "$SEED_LESSONS" \
  --password "$LOADTEST_PASSWORD" \
  --output /tmp/repetcrm_loadtest_users.json

"${COMPOSE[@]}" exec -T backend cat /tmp/repetcrm_loadtest_users.json > "$USERS_JSON"

SUMMARY_JSON="$RESULTS_DIR/summary-${SCENARIO}-${TIMESTAMP}.json"

echo "==> Running k6 scenario: $SCENARIO"
docker run --rm --network host \
  -v "$ROOT/deploy/loadtest/k6:/scripts:ro" \
  -v "$RESULTS_DIR:/results" \
  -v "$USERS_JSON:/data/users.json:ro" \
  -e BASE_URL="$BASE_URL" \
  -e USERS_FILE=/data/users.json \
  -e VUS="$TUTORS" \
  -e RAMP_UP="${RAMP_UP:-30s}" \
  -e STEADY="${STEADY:-2m}" \
  -e RAMP_DOWN="${RAMP_DOWN:-20s}" \
  -e THINK_TIME="${THINK_TIME:-1}" \
  "$K6_IMAGE" run \
  --summary-export="/results/$(basename "$SUMMARY_JSON")" \
  "/scripts/${SCENARIO}.js"

echo ""
echo "==> Done."
echo "    Users file:  $USERS_JSON"
echo "    Summary JSON: $SUMMARY_JSON"
echo ""
echo "Pass criteria (tutor-daily): http_req_failed < 2%, p95 < 800ms"
echo "Cleanup: ./deploy/scripts/loadtest.sh --cleanup"
