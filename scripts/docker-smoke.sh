#!/usr/bin/env bash
set -Eeuo pipefail

compose=(docker compose -p medcheck-infra-smoke -f docker-compose.yml)

cleanup() {
  "${compose[@]}" down --volumes --remove-orphans
}
trap cleanup EXIT

"${compose[@]}" config --quiet
"${compose[@]}" up --detach --wait postgres
"${compose[@]}" exec --no-TTY postgres \
  psql --username "${POSTGRES_USER:-medcheck}" --dbname "${POSTGRES_DB:-medcheck}" \
  --set ON_ERROR_STOP=1 --command 'SELECT 1;'
