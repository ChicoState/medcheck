# Spec: User and health-data foundation

## Status

Approved — 2026-10-07. User requested a custom account database with date of
birth, gender, and a personal medication list.

## Objective

Establish a private, database-only foundation for a Medcheck account. Each
account has a unique email address, an optional profile containing date of
birth and self-described gender, and zero or more named medications. The
foundation must leave future registration, login, API, UI, medication dosage,
and clinical interpretation out of scope.

### Success criteria

- Django uses the project-owned user model from the first database migration.
- Email is the unique account identifier and Django password hashes remain
  managed by Django; no plaintext passwords are stored.
- A user can have at most one profile; a profile may have a date of birth and
  optional self-described gender.
- Each medication belongs to exactly one profile and stores only its supplied
  name.
- Database migrations and model tests run successfully against PostgreSQL.

## Technology and commands

- Django 5.2 ORM and its built-in authentication primitives.
- PostgreSQL, configured through the existing `DATABASE_URL` setting.

```bash
(cd backend && uv run python manage.py makemigrations accounts)
(cd backend && uv run python manage.py migrate)
(cd backend && uv run pytest tests/accounts)
(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=tests)
git diff --check
```

## Project structure

```text
backend/accounts/                  Django account and health-profile models
backend/accounts/migrations/       Schema migration
backend/tests/accounts/            Database-model tests
docs/specs/                        Approved implementation specifications
docs/decisions/                    Durable data-model decisions
```

## Data model and style

`User` extends Django's `AbstractUser`, removes the separate username, and
uses a unique email address as `USERNAME_FIELD`. `HealthProfile` is a
one-to-one extension of `User`; `Medication` has a foreign key to
`HealthProfile` and a human-entered name. All health fields are optional or
absent by default so account creation does not force disclosure.

```python
class Medication(models.Model):
    profile = models.ForeignKey("HealthProfile", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
```

## Testing strategy

- Write database-model tests before model code.
- Prove that duplicate account email addresses are rejected.
- Prove that one profile is permitted per user.
- Prove that medications are scoped to their owning profile and are removed
  when that profile is removed.
- Run the complete backend quality suite after the migration is generated.

## Security and privacy boundaries

- **Always:** use Django's password hashing and ORM; collect only the approved
  fields; keep date of birth, gender, and medications out of logs and tests
  except synthetic fixtures; protect future access with authenticated
  ownership checks.
- **Ask first:** registration/login flows, public API or UI, new health or
  demographic fields, sharing data, retention/deletion policy, exporting data,
  or connecting medication names to clinical conclusions.
- **Never:** store plaintext passwords, make health details public, infer
  diagnoses or interactions from these records, or commit real user data or
  credentials.

## Migration guardrail

`AUTH_USER_MODEL` must be configured before running `migrate` against a real
database. If a database has already created Django's default `auth_user`
table, this feature needs a separate, reviewed migration plan rather than an
in-place switch.

## Open questions

- The requested word “gender” is modeled as optional, self-described text;
  no inference or required category is imposed.
- Medication entries intentionally do not include dose, schedule, prescribing
  clinician, or clinical verification. Those need their own reviewed scope.
