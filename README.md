# Medcheck

## Status

MedCheck offers live openFDA drug-label search and detail pages. Signed-in users
can save product labels to a private My Medication library and remove them later.
The Django account API uses session authentication and CSRF protection. This is
a reference tool, not personal medical advice or a medication regimen tracker.

## Repository map

- `docker/backend.Dockerfile` — non-root Python and uv tooling image; it is not
  a runnable application image until a backend entrypoint is implemented.
- `docker-compose.yml` — local PostgreSQL 17.6 service with a named volume and
  readiness health check.
- `scripts/docker-smoke.sh` — disposable PostgreSQL readiness and `SELECT 1`
  smoke test.
- `backend/` — Django account and medication APIs, openFDA adapter, migrations,
  locked dependencies, and tests.
- `web/` — React/Vite search, detail, and saved-library pages with browser tests.
- `.github/workflows/pr-checks.yml` — secret scanning plus backend and web
  quality checks, including the web build and Playwright tests.
- `.github/dependabot.yml` — weekly dependency-update configuration.
- `infrastructure_plan.md` — the approved infrastructure plan and source of
  truth for future configuration.
- `.agents/skills/` — local agent skills.
- `docs/specs/` — implementation specifications and scope boundaries.

## Getting Started

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   or Docker Engine with Compose v2, [uv](https://docs.astral.sh/uv/getting-started/installation/),
   and Node.js 22.23.3 with Corepack. The version is recorded in
   `.node-version`. Install [Python 3.13](https://www.python.org/downloads/) or
   allow uv to install its managed Python 3.13 runtime. The Docker image supplies
   Python and uv only for Docker work; host tools support editor and local
   quality-check workflows.
2. Copy the non-secret local defaults and export them for Django commands:

   ```bash
   cp .env.example .env
   set -a
   source .env
   set +a
   ```

   Docker Compose reads `.env` automatically. Django reads environment variables
   from the shell, so source the file again in each new shell before running
   Django commands. Never place a production secret in this file.

3. Install the locked tooling dependencies:

   ```bash
   (cd backend && uv sync --all-groups --frozen)
   (cd web && corepack enable && pnpm install --frozen-lockfile)
   (cd web && pnpm exec playwright install chromium)
   ```

4. Build the development-tooling image:

   ```bash
   docker build --file docker/backend.Dockerfile --tag medcheck-backend-tooling .
   ```

5. Start PostgreSQL locally:

   ```bash
   docker compose up --detach postgres
   ```

6. Start the local application:

   ```bash
   ./scripts/dev.sh
   ```

   Open `http://127.0.0.1:5173`. Press Ctrl+C in that terminal to stop both
   the Django API and Vite web server. The script runs Django migrations using
   `.env` when available, or the safe values in `.env.example`.

   The default database is local SQLite. To use the local PostgreSQL service,
   set `DATABASE_URL=postgresql://medcheck:medcheck_local_only@127.0.0.1:5432/medcheck`
   in your untracked `.env` before starting the script. Set `OPENFDA_API_KEY`
   there as well for live provider use; a key is optional for a limited local
   trial but required before public deployment. Do not commit these values.

7. Run the available backend, web, and browser checks, then clean up the Docker
   foundation:

   ```bash
   (cd backend && uv run python manage.py check && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=accounts --cov=medications && uv run bandit --quiet --recursive accounts config medications)
   (cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm test:e2e)
   ./scripts/docker-smoke.sh
   docker compose down --volumes
   ```

The local database is exposed only on `127.0.0.1:5432` by default. Change
`POSTGRES_PORT` in an untracked `.env` if that port is occupied. Reset local
database data with `docker compose down --volumes`.

Playwright verifies the search, detail, and saved-library journey with mocked
provider responses. The backend CI job runs against PostgreSQL. Saved labels
are personal health-related data; use only test data locally, and delete saved
relationships from My Medication when no longer needed. A production release
workflow remains deferred until a hosting
provider is selected.

For public deployment, configure managed PostgreSQL with a TLS-enabled
`DATABASE_URL` (for example, `?sslmode=require`), a server-side
`OPENFDA_API_KEY`, and a shared Django cache for search throttling. Ensure any
reverse proxy or tracing system redacts the `q` parameter from access logs;
the local browser history still contains `/search?q=...`. The development
server suppresses its access log for this reason. Production host, backup,
retention, and monitoring settings must be reviewed before launch.

## Troubleshooting

For local medication flows, run `./scripts/dev.sh`, search a medication name,
open an FDA product label, and sign in to save it. My Medication appears in the
menu after authentication and the session survives a reload. Product labels
can represent different manufacturers and formulations of similarly named
medications; always check the source and consult a healthcare professional.

Browser UI tests use controlled API responses. To also run the real account
workflow against a Django server using an isolated test database on port 8000,
run `cd web && MEDCHECK_LIVE_AUTH=1 pnpm test:e2e`.

- **Docker socket permission denied:** ensure Docker Desktop/Engine is running
  and that your user has permission to use the Docker daemon.
- **Port 5432 is occupied:** set `POSTGRES_PORT=127.0.0.1:5433` in `.env` and
  restart the Compose service.
- **A stale database is causing unexpected results:** run `docker compose down
  --volumes` before starting again.
- **Django reports a missing `DJANGO_SECRET_KEY`:** source the untracked `.env`
  into the current shell as shown above.
- **Node reports an unsupported engine:** select Node 22.23.3 from
  `.node-version`; Node 24 is outside the supported project range. Homebrew's
  `node@22` is keg-only, so add `/opt/homebrew/opt/node@22/bin` to `PATH` when
  using that installation.
- **`uv` or `pnpm` is missing:** install uv or run `corepack enable` under Node
  22, then rerun the locked install command.
- **`./scripts/dev.sh` reports a missing command:** run the dependency
  installation commands from Getting Started. On Apple Silicon Homebrew setups,
  the script automatically adds Node 22's `pnpm` location to its PATH.
