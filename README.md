# Medcheck

## Status

Infrastructure setup has begun. The repository currently provides a pinned
Docker development-tooling image and a local PostgreSQL service; no production
Django, React, or React Native application code exists yet.

## Repository map

- `docker/backend.Dockerfile` — non-root Python and uv tooling image; it is not
  a runnable application image until a backend entrypoint is implemented.
- `docker-compose.yml` — local PostgreSQL 17.6 service with a named volume and
  readiness health check.
- `scripts/docker-smoke.sh` — disposable PostgreSQL readiness and `SELECT 1`
  smoke test.
- `infrastructure_plan.md` — the approved infrastructure plan and source of
  truth for future configuration.
- `.agents/skills/` — local agent skills.
- `backend/`, `web/`, `mobile/`, and `tests/` — not created yet.

## Getting Started

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   or Docker Engine with Compose v2, then confirm `docker version` and
   `docker compose version` succeed.
2. Optionally copy the non-secret local database defaults:

   ```bash
   cp .env.example .env
   ```

3. Build the development-tooling image:

   ```bash
   docker build --file docker/backend.Dockerfile --tag medcheck-backend-tooling .
   ```

4. Start PostgreSQL locally:

   ```bash
   docker compose up --detach postgres
   ```

5. Verify and clean up the Docker foundation:

   ```bash
   ./scripts/docker-smoke.sh
   docker compose down --volumes
   ```

The local database is exposed only on `127.0.0.1:5432` by default. Change
`POSTGRES_PORT` in an untracked `.env` if that port is occupied. Reset local
database data with `docker compose down --volumes`.

Python, uv, Node.js/pnpm, Android Studio/SDK, and Xcode remain host
prerequisites for their respective future application development workflows.
Docker does not replace native mobile SDKs, signing, or notarization.

## Troubleshooting

- **Docker socket permission denied:** ensure Docker Desktop/Engine is running
  and that your user has permission to use the Docker daemon.
- **Port 5432 is occupied:** set `POSTGRES_PORT=127.0.0.1:5433` in `.env` and
  restart the Compose service.
- **A stale database is causing unexpected results:** run `docker compose down
  --volumes` before starting again.
