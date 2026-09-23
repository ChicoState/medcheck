# Medcheck

## Status

The repository has a web-only development foundation: pinned backend and web
tooling, a local PostgreSQL service, and pull-request checks. No production
Django or React application code exists yet.

## Repository map

- `docker/backend.Dockerfile` — non-root Python and uv tooling image; it is not
  a runnable application image until a backend entrypoint is implemented.
- `docker-compose.yml` — local PostgreSQL 17.6 service with a named volume and
  readiness health check.
- `scripts/docker-smoke.sh` — disposable PostgreSQL readiness and `SELECT 1`
  smoke test.
- `backend/` — Python/Django tooling, locked dependencies, and infrastructure
  probes; no Django project or API code exists yet.
- `web/` — React/Vite tooling, locked dependencies, and infrastructure probes;
  no page, component, or Vite entrypoint exists yet.
- `.github/workflows/pr-checks.yml` — web-only infrastructure quality checks.
- `.github/dependabot.yml` — weekly dependency-update configuration.
- `infrastructure_plan.md` — the approved infrastructure plan and source of
  truth for future configuration.
- `.agents/skills/` — local agent skills.
- `docs/` and production application source directories — not created yet.

## Getting Started

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   or Docker Engine with Compose v2, [Python 3.13](https://www.python.org/downloads/),
   [uv](https://docs.astral.sh/uv/getting-started/installation/), and Node.js
   22 LTS with Corepack enabled. The Docker image supplies Python and uv only
   for Docker work; host tools support editor and local quality-check workflows.
2. Optionally copy the non-secret local database defaults:

   ```bash
   cp .env.example .env
   ```

3. Install the locked tooling dependencies:

   ```bash
   (cd backend && uv sync --all-groups --frozen)
   (cd web && corepack enable && pnpm install --frozen-lockfile)
   ```

4. Build the development-tooling image:

   ```bash
   docker build --file docker/backend.Dockerfile --tag medcheck-backend-tooling .
   ```

5. Start PostgreSQL locally:

   ```bash
   docker compose up --detach postgres
   ```

6. Run the available infrastructure checks and clean up the Docker foundation:

   ```bash
   (cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=tests)
   (cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test)
   ./scripts/docker-smoke.sh
   docker compose down --volumes
   ```

The local database is exposed only on `127.0.0.1:5432` by default. Change
`POSTGRES_PORT` in an untracked `.env` if that port is occupied. Reset local
database data with `docker compose down --volumes`.

Vite builds and Playwright end-to-end tests are intentionally unavailable until
the future React application supplies an entrypoint and workflows. A production
release workflow is also deferred until a hosting provider is selected.

## Troubleshooting

- **Docker socket permission denied:** ensure Docker Desktop/Engine is running
  and that your user has permission to use the Docker daemon.
- **Port 5432 is occupied:** set `POSTGRES_PORT=127.0.0.1:5433` in `.env` and
  restart the Compose service.
- **A stale database is causing unexpected results:** run `docker compose down
  --volumes` before starting again.
- **`uv` or `pnpm` is missing:** install the host prerequisite from the links
  above, then rerun the locked install command.
