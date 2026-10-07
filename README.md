# Medcheck

## Status

The repository has minimal Django and React/Vite application scaffolds, a local
PostgreSQL service, and pull-request checks. FDA drug-label interaction text
can be imported into PostgreSQL; it is source material, not a complete
normalized interaction knowledge base or clinical advice. No production API or
product UI exists yet. A private user-data foundation stores account identity,
optional date of birth and gender, and user-listed medication names.
The repository has a minimal Django scaffold, a React/Vite landing-page
prototype, a local PostgreSQL service, and pull-request checks. The landing page
accepts a local search term but does not query medical information. No
production API, domain models, authentication, or persistent product workflow
exists yet.

## Repository map

- `docker/backend.Dockerfile` — non-root Python and uv tooling image; it is not
  a runnable application image until a backend entrypoint is implemented.
- `docker-compose.yml` — local PostgreSQL 17.6 service with a named volume and
  readiness health check.
- `scripts/docker-smoke.sh` — disposable PostgreSQL readiness and `SELECT 1`
  smoke test.
- `backend/` — Django project, private account/health-data and FDA-label import
  applications, Python/Django tooling, locked dependencies, and infrastructure
  probes; no API exists yet.
- `web/` — React/Vite entrypoint, locked dependencies, infrastructure probes, and
  the initial application shell; no product page or business UI exists yet.
- `.github/workflows/pr-checks.yml` — web-only infrastructure quality checks.
- `backend/` — minimal Django project scaffold, Python/Django tooling, locked
  dependencies, and infrastructure probes; no API or business code exists yet.
- `web/` — React/Vite landing-page prototype, locked dependencies,
  infrastructure probes, and Playwright browser tests.
- `.github/workflows/pr-checks.yml` — secret scanning plus backend and web
  quality checks, including the web build and Playwright tests.
- `.github/dependabot.yml` — weekly dependency-update configuration.
- `infrastructure_plan.md` — the approved infrastructure plan and source of
  truth for future configuration.
- `.agents/skills/` — local agent skills.
- `docs/specs/` — proposed application specifications awaiting review.
- `docs/decisions/` — durable architecture decision records.
- Production application source directories — not created yet.
- `docs/specs/` — implementation specifications and scope boundaries.
- Production API and domain application packages — not created yet.

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

6. Configure the backend to use that local database, apply migrations, and
   optionally import FDA label source text:

   ```bash
   export DATABASE_URL='postgresql://medcheck:medcheck_local_only@127.0.0.1:5432/medcheck'
   export DJANGO_SECRET_KEY='local-development-only'
   (cd backend && uv run python manage.py migrate)
   (cd backend && uv run python manage.py import_fda_drug_labels --max-pages 1)
   ```

   The import command only uses FDA's fixed Drug Labeling endpoint. It retains
   raw `drug_interactions` text by label version; it does not infer drug pairs,
   severity, contraindications, or patient-specific guidance. Increase
   `--max-pages` (up to 100) deliberately when importing a larger batch.

7. Run the available checks and clean up the Docker foundation:
6. Run the available backend, web, and browser checks, then clean up the Docker
   foundation:

   ```bash
   (cd backend && uv run python manage.py check && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=tests)
   (cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm test:e2e)
   ./scripts/docker-smoke.sh
   docker compose down --volumes
   ```

The local database is exposed only on `127.0.0.1:5432` by default. Change
`POSTGRES_PORT` in an untracked `.env` if that port is occupied. Reset local
database data with `docker compose down --volumes`.

Playwright currently verifies the landing-page layout and local search-form
behavior. A production release workflow remains deferred until a hosting
provider is selected.

## Troubleshooting

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
