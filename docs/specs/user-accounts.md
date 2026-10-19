# User Accounts Specification

## Objective

Provide one private account per user for the MedCheck web client. Account
identity is owned by Django and persisted in the configured relational
database. This slice does not add medical records or saved-medicine data.

## Authentication contract

- Registration accepts `email`, `password`, and `password_confirmation`.
- Email addresses are normalized to lowercase and are unique, case-insensitively.
- Django's built-in password validators protect passwords; raw passwords are
  never stored or returned.
- Successful registration signs the user in with a Django session.
- Login accepts `email` and `password` and creates a Django session.
- Logout is a `POST` and clears the session.
- `GET /api/auth/me/` returns the current user's id and email, or `401`.
- `GET /api/auth/csrf/` establishes a CSRF cookie for browser clients.
- Mutating endpoints require the Django CSRF token and use same-origin cookies.

## Error contract

Invalid requests return `400` with an object containing field-level messages.
Duplicate or already-registered emails return a generic email error and do not
reveal account details beyond the fact that registration cannot proceed.
Invalid login returns a generic `400` error without identifying which
credential was incorrect.

## Privacy and scope

The API never returns password material. Authentication is session-based and
same-origin; no token is exposed to JavaScript. Authorization for future
user-owned resources must derive ownership from `request.user`, never from a
client-provided user id.

## Web experience

- The Account popover offers Sign in followed by Create account when signed out.
- Sign in accepts email and password. Create account accepts email, password,
  and confirmation. Validation errors stay beside the form.
- A successful action updates the navigation immediately. Session status is
  restored from Django on reload.
- Signed-in users see their email and Sign out in the Account popover.
- The menu shows My Medication only for signed-in users. It opens
  `/my-medication`, the current empty medication page.
- Vite proxies `/api` to the local Django server at port 8000 during development.
