#!/usr/bin/env bash
set -Eeuo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

if [[ -x /opt/homebrew/opt/node@22/bin/pnpm ]]; then
  export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
fi

for command in uv pnpm; do
  if ! command -v "$command" >/dev/null; then
    printf 'Missing required command: %s\n' "$command" >&2
    exit 1
  fi
done

environment_file=.env.example
if [[ -f .env ]]; then
  environment_file=.env
fi
set -a
source "$environment_file"
set +a

cleanup() {
  trap - EXIT INT TERM
  kill "${django_pid:-}" "${vite_pid:-}" 2>/dev/null || true
  wait "${django_pid:-}" "${vite_pid:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd backend && uv run python manage.py migrate --noinput)

(cd backend && exec uv run python manage.py runserver 127.0.0.1:8000) &
django_pid=$!
(cd web && exec pnpm dev -- --host 127.0.0.1) &
vite_pid=$!

printf 'MedCheck is starting at http://127.0.0.1:5173\n'
printf 'Press Ctrl+C to stop Django and Vite.\n'

wait "$django_pid"
