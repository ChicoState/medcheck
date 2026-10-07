# ADR-002: Use a custom email-based user model with a separate health profile

## Status

Accepted — 2026-10-07.

## Context

Medcheck needs account records with date of birth, gender, and a private list
of medications. Django's built-in user model cannot safely be substituted
after it has been migrated in a production database. Health details should not
be spread across authentication fields or gathered by default at account
creation.

## Decision

Create a project-owned Django `User` model based on `AbstractUser`, using a
unique email address as the login identifier. Store date of birth and optional
self-described gender in a one-to-one `HealthProfile`, and store each
user-listed medication as a child record of that profile.

## Alternatives considered

### Default Django `auth_user` table

It provides authentication data immediately but makes later customization of
the account model expensive. Rejected before first migration.

### Put health details directly on `User`

It is initially fewer tables, but mixes authentication and sensitive health
data. Rejected in favor of a separate profile boundary.

### Model medication as a link to imported FDA labels

The imported label data is raw source material, not a normalized medication
catalog. Linking it now could imply clinical matching or completeness.
Deferred.

## Consequences

- The project must set `AUTH_USER_MODEL` before its first real migration.
- Future code must use `settings.AUTH_USER_MODEL` in relationships rather than
  importing Django's default user model.
- Future access routes must enforce ownership and must not expose health data
  in logs or unauthenticated responses.
