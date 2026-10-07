# Implementation Plan: FDA drug-label interaction import

## Status

Draft — awaiting approval before implementation.

## Overview

Implement the approved raw FDA drug-label interaction import as a small Django
application backed by the repository's existing PostgreSQL service. The work
is sequential because the settings, model/migration, parser, and command each
depend on the previous layer. It adds no HTTP API or user interface.

## Architecture decisions

- PostgreSQL is configured through environment-derived settings, consistent
  with the approved infrastructure plan; a local SQLite database is not the
  application source of truth.
- A `(set_id, version)` database constraint identifies one FDA SPL label
  version and makes the import idempotent.
- The importer uses only Python's standard-library HTTP client against a
  fixed HTTPS FDA endpoint, avoiding a new runtime dependency.
- A parsing/service boundary validates source records before atomic ORM writes;
  tests provide a fake transport and never call FDA.

## Dependency graph

```text
PostgreSQL settings
        |
        v
model + migration
        |
        v
validated FDA record parser
        |
        v
bounded import command
        |
        v
operator documentation and complete verification
```

## Tasks

### Task 1: Configure PostgreSQL-backed Django runtime

**Description:** Replace the scaffold's SQLite-only runtime setting with a
validated PostgreSQL configuration derived from local environment variables,
and establish the test-database configuration needed for Django application
tests.

**Acceptance criteria:**

- [ ] The backend connects to the local Compose PostgreSQL service without a
  committed connection string or credential.
- [ ] Missing or malformed required database configuration fails clearly.
- [ ] Django tests run against an isolated test database, not production data.

**Verification:**

- [ ] `docker compose up --detach postgres`
- [ ] `(cd backend && uv run python manage.py check)`
- [ ] `(cd backend && uv run pytest)`

**Dependencies:** None.

**Files likely touched:** `backend/config/settings.py`, `.env.example`,
`backend/tests/`, `README.md`.

**Estimated scope:** M (4 files).

### Task 2: Add the provenance-preserving label model

**Description:** Create the `drug_labels` Django app, write model tests first,
then add `DrugLabelInteraction`, its migration, and the unique label-version
constraint.

**Acceptance criteria:**

- [ ] The model stores every approved spec field, including raw interaction
  text, source URL, hash, and UTC import time.
- [ ] The database rejects a duplicate `(set_id, version)` row.
- [ ] Migrations apply cleanly to PostgreSQL.

**Verification:**

- [ ] `(cd backend && uv run pytest tests/drug_labels/test_models.py)`
- [ ] `(cd backend && uv run python manage.py migrate --plan)`

**Dependencies:** Task 1.

**Files likely touched:** `backend/drug_labels/apps.py`,
`backend/drug_labels/models.py`, `backend/drug_labels/migrations/0001_initial.py`,
`backend/config/settings.py`, `backend/tests/drug_labels/test_models.py`.

**Estimated scope:** M (5 files).

### Task 3: Build and test the bounded FDA record parser

**Description:** Add a pure parser that accepts only the expected openFDA
response shape, preserves the specified metadata, rejects malformed records,
and produces deterministic payload hashes.

**Acceptance criteria:**

- [ ] Valid representative FDA records produce a complete import value.
- [ ] Missing identifiers, blank interaction text, and invalid types are
  rejected without database writes.
- [ ] Equivalent normalized source data produces the same SHA-256 hash.

**Verification:**

- [ ] `(cd backend && uv run pytest tests/drug_labels/test_parser.py)`
- [ ] `(cd backend && uv run ruff check drug_labels tests/drug_labels)`

**Dependencies:** Task 2.

**Files likely touched:** `backend/drug_labels/fda.py`,
`backend/tests/drug_labels/test_parser.py`.

**Estimated scope:** S (2 files).

### Checkpoint: Storage foundation

- [ ] Tasks 1–3 pass their targeted tests against PostgreSQL.
- [ ] No source payload or secret appears in the diff.
- [ ] The schema and parser are reviewed before external import behavior is
  added.

### Task 4: Add the explicit, bounded import command

**Description:** Write command tests first, then implement
`import_fda_drug_labels`. It pages through the fixed FDA endpoint with an
allowlisted query, timeout, response-size cap, bounded retries, and atomic
upsert behavior.

**Acceptance criteria:**

- [ ] A successful fake paginated import creates expected rows and prints only
  counts/identifiers.
- [ ] A repeat import leaves unchanged label versions unmodified; a changed
  hash updates the matching row.
- [ ] Transport failures, oversized responses, and malformed pages report a
  safe error and leave affected rows unchanged.

**Verification:**

- [ ] `(cd backend && uv run pytest tests/drug_labels/test_import_command.py)`
- [ ] `(cd backend && uv run python manage.py import_fda_drug_labels --help)`

**Dependencies:** Task 3.

**Files likely touched:** `backend/drug_labels/management/commands/import_fda_drug_labels.py`,
`backend/drug_labels/fda.py`,
`backend/tests/drug_labels/test_import_command.py`.

**Estimated scope:** S (3 files).

### Task 5: Document operation and run the complete quality suite

**Description:** Add the operator command and safety limits to the README,
then validate the finished migration/import path and existing tooling.

**Acceptance criteria:**

- [ ] README documents starting PostgreSQL, applying migrations, manual import,
  and the data's non-clinical scope.
- [ ] The approved spec and ADR accurately reflect implementation.
- [ ] All relevant backend and repository checks pass.

**Verification:**

- [ ] `(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=tests)`
- [ ] `docker compose config --quiet`
- [ ] `git diff --check`

**Dependencies:** Task 4.

**Files likely touched:** `README.md`, `docs/specs/drug-label-interactions.md`,
`docs/decisions/adr-001-fda-label-interaction-source.md`.

**Estimated scope:** S (3 files).

### Checkpoint: Complete

- [ ] All specification acceptance criteria are met.
- [ ] The import is operator-triggered and makes no real FDA request during
  tests.
- [ ] No API/UI or normalized clinical interaction claims were introduced.
- [ ] Full quality suite and `git diff --check` pass.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| FDA records vary by product/version | High | Strict payload validation; retain raw text and provenance rather than infer pairs. |
| Upstream outage or slow response | Medium | Fixed endpoint, timeout, bounded retries, manual execution, safe failure. |
| Large response/pagination cost | Medium | Explicit page size, response-size cap, and bounded traversal. |
| Duplicate/stale data | Medium | Database uniqueness and source-hash-aware upserts. |
| Medical overclaim | High | No severity/pair extraction or user-facing advice; state source-only scope in docs. |

## Parallelization

None during the first implementation. Each task changes a dependency of the
next one; sequential tested increments keep migrations and import behavior
reviewable.
