# Basic username and password accounts

## Objective and scope

Users register with only a username and password, sign in, remain signed in
across refreshes, and sign out. Accounts persist in PostgreSQL. Registration
signs the new user in immediately. Existing navigation uses the server's session
state, including access to the Saved Medicines empty page.

No social login, email requirement, email verification, password recovery, admin
portal work, or medicine persistence is included. Ordinary registration never
creates staff or superusers. The infrastructure plan records the user-approved
scope; this specification describes its implementation.

## Architecture and MVC boundaries

- Model: Django's built-in `User` and database-backed sessions, using their
  existing migrations. Username constraints and password validation belong in
  `backend/accounts/forms.py`; passwords use Django's hashing functions.
- Controller: `backend/accounts/views.py` handles JSON input, sessions, responses,
  and request throttling. Normal Django CSRF middleware protects all writes,
  including anonymous registration and login.
- View: React account forms in `web/src/auth/AuthPage.tsx`. API requests and
  session state are isolated in `api.ts` and `useAuth.ts`; presentation components
  do not store credentials or enforce backend permissions.
- Django uses the existing PostgreSQL service. There is no SQLite fallback.
  Database configuration comes from environment variables.
- Vite forwards `/api` to Django while preserving the browser's Host header.
  This keeps browser requests same-origin without CORS or browser token storage.
  A deployed frontend requires equivalent same-origin routing over HTTPS.

Use the installed Django, React, TypeScript and PostgreSQL versions. No new
dependency is required. Follow the existing Ruff/Prettier naming and formatting.
For example, handlers return `JsonResponse({"errors": {"__all__": [message]}},
status=400)` rather than exposing exception details.

## API contract

| Method | Path | Input | Success |
| --- | --- | --- | --- |
| GET | `/api/auth/session/` | None | 200 session envelope |
| POST | `/api/auth/register/` | `{"username":"…","password":"…"}` | 201 session envelope, signed in |
| POST | `/api/auth/login/` | Same credentials | 200 session envelope, signed in |
| POST | `/api/auth/logout/` | `{}` | 200 session envelope, signed out |

The envelope is `{"user":{"id":1,"username":"example"},"csrfToken":"…"}`;
`user` is `null` when signed out. Never return passwords or privilege fields.
All session envelopes use `Cache-Control: no-store`. The browser first gets a
session envelope and sends its token in `X-CSRFToken` on POST requests. After
authentication, use the returned token because Django rotates it on login.

Errors use `{"errors":{"field":["message"]}}`, with `__all__` for general
errors. Invalid input or credentials return 400, failed CSRF checks return 403,
and throttled attempts return 429. Login errors do not distinguish a nonexistent
user from a bad password or inactive account. Only username and password are
accepted as credential fields. Usernames follow Django's normalization and
case-sensitive uniqueness; passwords are not trimmed.

## Implementation and verification sequence

1. Configure PostgreSQL and environment variables. Apply built-in migrations;
   verify Django checks and migration consistency against PostgreSQL.
2. Add backend tests for the contract before implementing registration and
   authentication. Verify constraints, hashing, duplicate handling, inactive
   users, invalid input, CSRF enforcement, logout invalidation and throttling.
3. Implement the API client, session state, registration/sign-in forms, and
   navigation. Wait for session restoration before redirecting protected routes;
   provide loading, retry and validation feedback.
4. Add `web/tests/e2e/accounts.spec.ts` for real browser/API/database journeys.
   Use a dedicated test database and generated test usernames. Cover registration,
   refresh on Saved Medicines, logout, signing in again, duplicate registration,
   and invalid credentials. Retain landing-page tests.
5. Run formatting, lint, types, backend tests, security scan, web build and browser
   tests. Update CI and setup documentation to use the same services and checks.

## Validation commands

From the repository root, with dependencies installed:

```bash
set -a
source .env.example
set +a
docker compose up --detach --wait postgres
(cd backend && uv run python manage.py migrate --noinput && uv run python manage.py check && uv run python manage.py makemigrations --check --dry-run)
(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=accounts && uv run bandit --quiet --recursive accounts config)
(cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build)
docker compose exec -T postgres createdb -U medcheck medcheck_e2e
(cd web && POSTGRES_DB=medcheck_e2e pnpm test:e2e)
git diff --check
```

Create `medcheck_e2e` only once. Browser tests migrate that database and start
Django on port 8010 and Vite on 5173. Do not point browser tests at user data.
pytest creates and destroys its own `test_` database. See README for dev commands.

## Boundaries and limitations

Always preserve CSRF protection, validate on the server, keep real secrets out of
tracked files, and test with disposable accounts. Do not add excluded account or
medical features without a new scope decision. Infrastructure-only smoke tests
must continue to clean up only their own resources.

Login and registration share a basic per-IP, per-process limit of 20 attempts per
minute. A public deployment needs a shared cache or edge rate limiter across
workers, plus HTTPS and appropriate allowed hosts. This task does not select a
hosting provider or deploy the application.

## Framework references

- [Django authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/)
- [Django CSRF protection](https://docs.djangoproject.com/en/5.2/howto/csrf/)
