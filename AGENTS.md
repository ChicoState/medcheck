# Agent Guidance

## Current status

`infrastructure_plan.md` is the source of truth. The web-only tooling and Docker
foundation are in place, but production application code has not been created. Do not introduce
pages, routes, API handlers, domain models, authentication, or business data
while performing infrastructure work.

## Repository map

- `infrastructure_plan.md` — approved decisions; revise it through the
  planning skill before changing architectural choices.
- `docker/backend.Dockerfile`, `docker-compose.yml`, and `.dockerignore` —
  Docker tooling and local PostgreSQL only.
- `scripts/docker-smoke.sh` — infrastructure-owned smoke test.
- `backend/` — Python dependency/tool configuration and infrastructure-only tests;
  no Django application package exists yet.
- `web/` — React/Vite dependency/tool configuration and infrastructure-only tests;
  no React application entrypoint exists yet.
- `.github/workflows/pr-checks.yml` — web-only pull-request quality checks.
- `.github/workflows/release.yml` — not created; it requires a selected hosting provider.
- `docs/` — not created yet.
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

Run `docker compose up --detach postgres` to start the local database and
`docker compose down --volumes` to stop it and remove its named volume. Run
`./scripts/docker-smoke.sh` for a disposable readiness test; it always cleans
up its Compose project and volume. Never place real secrets in `.env`, images,
workflow logs, or tracked files.

## Verification and change checklist

For Docker changes, run:

```bash
docker build --file docker/backend.Dockerfile --tag medcheck-backend-tooling .
docker compose config --quiet
./scripts/docker-smoke.sh
(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=tests)
(cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test)
git diff --check
```

Keep CI commands equivalent once workflows are added. Update README and this
file whenever paths, setup commands, services, or verification steps change.
