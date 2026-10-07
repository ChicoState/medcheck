# Agent Guidance

## Current status

`infrastructure_plan.md` is the source of truth for architectural decisions. The
web tooling, MedCheck landing-page prototype, Playwright tests, Docker
foundation, and minimal Django project scaffold are in place. The landing page
only echoes a local search term; no medical search, production API, domain
model, authentication, or persistence workflow exists. Do not expand product
behavior while performing infrastructure work.

## MVC design requirement

All agents must build application features with Model–View–Controller (MVC)
separation in mind. Keep data and business rules, presentation, and request
coordination separate so each responsibility can be maintained and tested
independently. Apply this within the approved React and Django architecture:

- **Model:** Django models own persistent domain data and constraints. Keep
  business rules in the backend model/domain layer, using focused services when
  a workflow spans models. React types and local state do not replace this layer.
- **View:** React components render data and collect user input. Keep domain
  rules and persistence logic out of presentation components; local UI state
  and simple UI event handlers may remain in components.
- **Controller:** Django/DRF request handlers coordinate input validation,
  authorization, domain operations, and responses. Keep handlers thin and
  delegate business rules to the model/domain layer. Isolate frontend API
  access and workflow coordination from rendering as features grow.

Django uses Model–Template–View (MTV) terminology: its API views perform much of
the controller responsibility described here, while React provides the user
interface. Follow framework conventions without requiring literal `controllers`
directories or unnecessary abstraction layers.

For each feature, identify these responsibilities in its specification and
review their separation during implementation. The current scaffold is not a
complete MVC implementation; apply this requirement as product behavior is built.

## Repository map

- `infrastructure_plan.md` — approved decisions; revise it through the
  planning skill before changing architectural choices.
- `docker/backend.Dockerfile`, `docker-compose.yml`, and `.dockerignore` —
  Docker tooling and local PostgreSQL only.
- `scripts/docker-smoke.sh` — infrastructure-owned smoke test.
- `backend/` — Django project scaffold, Python dependency/tool configuration, and
  infrastructure-only tests; no API or business application package exists yet.
- `web/` — React/Vite entrypoint, dependency/tool configuration, and
  the landing-page prototype with infrastructure and Playwright tests.
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
(cd backend && set -a && source ../.env.example && set +a && uv run python manage.py check)
(cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm test:e2e)
git diff --check
```

Keep CI commands equivalent once workflows are added. Update README and this
file whenever paths, setup commands, services, or verification steps change.
