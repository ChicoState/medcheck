# Spec: Private account workspace

## Status

Proposed — 2026-10-07.

## Objective

Provide the first usable Medcheck workflow: an individual can create an
account, sign in and out, provide their optional profile details, and manage
their own medication-name list. The browser must never receive a password
hash, session secret, or another person's health data.

## Architecture

The React/Vite client communicates with versionless, same-origin-relative
`/api/` endpoints. During local development, Vite proxies `/api/` to Django.
Django uses its built-in session cookie authentication; the session cookie is
HTTP-only and the client sends Django's CSRF token on every state-changing
request. No token is stored in localStorage or sessionStorage.

## API contract

All errors use `{ "error": { "code": string, "message": string } }`.

| Method | Path | Purpose | Response |
| --- | --- | --- | --- |
| GET | `/api/auth/csrf/` | Set CSRF cookie | `204` |
| POST | `/api/auth/register/` | Create and sign in an account | `201` current profile |
| POST | `/api/auth/login/` | Sign in by email and password | `200` current profile |
| POST | `/api/auth/logout/` | End current session | `204` |
| GET | `/api/me/` | Read signed-in profile | `200` current profile, `401` otherwise |
| PATCH | `/api/me/` | Update date of birth/gender | `200` current profile |
| GET | `/api/medications/` | List caller's medications | `200` list |
| POST | `/api/medications/` | Add one medication name | `201` medication |
| DELETE | `/api/medications/{id}/` | Delete the caller's medication | `204`; another user's ID returns `404` |

Date of birth is sent as ISO `YYYY-MM-DD`; gender remains optional
self-described text. Medication names are trimmed, nonempty, and capped at
the database's 255-character limit.

## User experience

- Signed-out visitors see one focused account form with a switch between
  create-account and sign-in modes.
- Signed-in visitors see their email, a profile form, and a medication list
  with an add field and a delete button on each medication.
- Forms have visible labels, inline errors, loading states, keyboard-native
  controls, and an announcement region for saved changes.
- A sign-out control returns the user to the account form.

## Project structure

```text
backend/accounts/              serializers, API views, URLs, and model tests
backend/tests/accounts/        API authorization and validation tests
web/src/                       account workspace and API client
web/tests/                     focused React tests
docs/specs/                    feature specification
```

## Commands

```bash
docker compose up --detach postgres
(cd backend && uv run pytest tests/accounts)
(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright)
(cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build)
git diff --check
```

## Security and boundaries

- **Always:** use Django password validators, generic failed-login messages,
  server-side authentication and ownership checks, CSRF protection, ORM access,
  and `HttpOnly` session cookies. Do not put sensitive values in browser
  storage, URLs, console logs, or error details.
- **Ask first:** email verification, password recovery, social login,
  multi-factor authentication, rate limiting infrastructure, account deletion,
  sharing data, additional health fields, or clinical medication advice.
- **Never:** reveal whether an email is registered during login, expose one
  user's profile or medication records to another user, or treat user-entered
  medication names as clinical data.

## Testing strategy

- Backend API tests cover registration, sign-in failure, authentication,
  profile updates, medication validation, and cross-user deletion denial.
- Web tests cover signed-out, signed-in, error, and medication-management
  states with mocked same-origin requests.
- A real browser smoke test verifies the account form after the local Django
  and Vite servers are available.

## Excluded from this slice

Email verification, password reset, account deletion, clinical interpretation,
dosage/schedule details, account settings beyond profile fields, and public API
documentation.
