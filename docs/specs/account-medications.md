# Spec: Account medications

## Objective

Give an individual a private account where they can register, sign in, add
medications, sign out, and sign in again to see the same records. The first
medication record contains a name, dosage, and frequency.

## Tech stack

- Django 5.2 with its built-in user model, password hashing, sessions, and
  CSRF protection.
- PostgreSQL for local and hosted persistent data; Django's test database is
  isolated from the developer database.
- React 19 and Vite 6 for the browser interface.

## Commands

```bash
docker compose up --detach postgres
(cd backend && set -a && source ../.env && set +a && uv run manage.py migrate)
(cd backend && set -a && source ../.env && set +a && uv run manage.py runserver)
(cd web && pnpm dev)
(cd backend && uv run pytest)
(cd web && pnpm typecheck && pnpm build)
```

## API contract

All endpoints are relative to `/api/`, use JSON, and return errors as
`{"error": {"code": "...", "message": "..."}}`.

| Method | Path | Request | Result |
| --- | --- | --- | --- |
| GET | `/api/csrf/` | — | Sets CSRF cookie and returns `{ "csrfToken": "..." }` |
| POST | `/api/auth/register/` | `email`, `password` | Creates and signs in account; `201` user |
| POST | `/api/auth/login/` | `email`, `password` | Signs in account; `200` user |
| POST | `/api/auth/logout/` | — | Clears the session; `204` |
| GET | `/api/auth/me/` | — | Current user or `401` |
| GET | `/api/medications/` | — | Current user's medications, newest first |
| POST | `/api/medications/` | `name`, `dosage`, `frequency` | Creates an account-owned medication; `201` |

Mutating requests include the CSRF token in `X-CSRFToken`. Unauthenticated
requests to private endpoints receive `401`; they never redirect to HTML.

## Structure and style

- `backend/medications/` owns the medication model, API views, URLs, and
  backend tests.
- `web/src/` owns the form-driven account and medication interface.
- `docs/specs/` records product contracts that inform both clients.
- Django models use `snake_case`; API JSON and React types use `camelCase`.

## Testing strategy

- Django integration tests prove registration, login/logout, validation,
  ownership isolation, and records surviving a new session.
- The browser flow proves the accessible React form can register, add a
  medication, sign out, sign back in, and display the persisted record.

## Boundaries

- Always: validate JSON at the API boundary, require a valid session for
  medication access, enforce CSRF for writes, and use Django migrations.
- Ask first: new medication fields, external identity providers, password-reset
  email, or exposing medications to another account.
- Never: store passwords or auth tokens in browser storage, return another
  user's records, commit a secret, or use medication data as medical advice.

## Success criteria

1. A new user can register with email and password, then sign out and sign in.
2. A signed-in user can save name, dosage, and frequency for a medication.
3. The same user sees that medication after a sign-out/sign-in cycle.
4. A different user receives no records belonging to the first user.
5. Invalid input, missing CSRF tokens, and anonymous private requests receive
   safe JSON errors.
