# Agent Guidance

## Current status

`infrastructure_plan.md` is the source of truth for architectural decisions. The
web tooling, Playwright tests, Docker foundation, Django session-based account
API, live openFDA label search, and private saved-medication library are in place.
Do not expand product behavior while performing infrastructure work.

## Repository map

- `infrastructure_plan.md` — approved decisions; revise it through the
  planning skill before changing architectural choices.
- `docker/backend.Dockerfile`, `docker/web.Dockerfile`, `docker-compose.yml`,
  and `.dockerignore` — Docker development images and local services.
- `scripts/docker-smoke.sh` — infrastructure-owned smoke test.
- `scripts/dev.sh` — starts local Django and Vite together.
- `backend/` — Django accounts, medications app, openFDA adapter, PostgreSQL
  configuration, Python tooling, and tests.
- `web/` — React/Vite search, detail, account, and saved-library UI with
  Playwright tests. Vite proxies `/api` to Django on port 8000.
- `.github/workflows/pr-checks.yml` — secret, backend, web, build, and browser
  pull-request quality checks.
- `.github/workflows/release.yml` — not created; it requires a selected hosting provider.
- `docs/specs/` — application and setup specifications.
- `.agents/skills/` — project-specific skills and instructions.

## Required reading and skill selection

Before changing files, read `infrastructure_plan.md`, this file, and relevant
local instructions. Use `infra-planner` for plan decisions, `infra-builder`
for infrastructure, `spec-driven-development` and `incremental-implementation`
for application work, `test-driven-development` for behavior changes,
`test-in-browser` or `browser-testing-with-devtools` for web verification,
`security-and-hardening` for untrusted-data/auth work,
`documentation-and-adrs` for durable decisions, `ci-cd-and-automation` for
workflows, `code-review-and-quality` before merging, and
`git-workflow-and-versioning` for every change.

## Docker lifecycle

Run `docker compose up --build --detach --wait` to start PostgreSQL, Django, and
Vite. Run `docker compose down --volumes` to stop the stack and remove named
volumes. Run `./scripts/docker-smoke.sh` for a disposable PostgreSQL readiness
test; it always cleans up its isolated Compose project and volume. Never place
real secrets in `.env`, images, workflow logs, or tracked files.

## Verification and change checklist

For Docker changes, run:

```bash
docker compose build backend web
docker compose config --quiet
docker compose up --detach --wait
./scripts/docker-smoke.sh
(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=accounts --cov=medications && uv run bandit --quiet --recursive accounts config medications)
(cd backend && set -a && source ../.env.example && set +a && uv run python manage.py check)
(cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm test:e2e)
git diff --check
docker compose down --volumes
```

Keep CI commands equivalent once workflows are added. Update README and this
file whenever paths, setup commands, services, or verification steps change.

For application development, prefer `docker compose up --build --detach --wait`.
It supplies uv, pnpm, Python, Node.js, PostgreSQL, applies migrations, and runs
both application servers. The host-based `./scripts/dev.sh` fallback loads local
environment defaults, uses SQLite unless `DATABASE_URL` is set, and stops both
servers on Ctrl+C. Do not use real patient data. Keep `OPENFDA_API_KEY`
server-side and untracked.
`MEDCHECK_LIVE_AUTH=1 pnpm test:e2e` additionally verifies accounts against a
running Django server with an isolated test database on port 8000.
