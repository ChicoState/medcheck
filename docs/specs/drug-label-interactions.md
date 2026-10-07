# Spec: FDA drug-label interaction import

## Status

Approved — 2026-09-30. Implementation planning is in progress.

## Objective

Store the raw `drug_interactions` text from FDA drug-label records in the
application's PostgreSQL database, together with enough immutable provenance
to identify the source label and its version. The feature supports later
product workflows; it does not determine whether two drugs interact.

### Acceptance criteria

- An operator can run one explicit Django management command to import label
  records that contain `drug_interactions` from the FDA openFDA Drug Labeling
  endpoint.
- Each stored record preserves the raw interaction text and its FDA label
  identity/version metadata.
- Re-running the command does not create duplicate records for the same label
  version.
- Malformed, oversized, or incomplete upstream records do not partially write
  data; they are reported without exposing response bodies in normal output.
- No API endpoint, product UI, user input, interaction-pair extraction,
  clinical severity, dosage recommendation, or automated scheduling is added.

## Data source and scope

- **Provider:** FDA openFDA Drug Labeling API, `https://api.fda.gov/drug/label.json`.
- **Selection:** records that include a nonempty `drug_interactions` section.
- **Meaning:** FDA labels have heterogeneous section text. Stored content is
  source material, not a normalized or complete drug--drug interaction
  knowledge base and not clinical advice.
- **Refresh:** operator-triggered only. No background task, cron job, or live
  user-request fetch is in scope.

## Data model

Create a Django application named `drug_labels` with one model,
`DrugLabelInteraction`:

| Field | Purpose |
| --- | --- |
| `set_id` | FDA SPL label identifier. |
| `version` | FDA label version, stored with `set_id` as the identity key. |
| `effective_time` | FDA label effective date/time if supplied. |
| `brand_name` | First reported brand name, if supplied. |
| `generic_name` | First reported generic name, if supplied. |
| `substance_names` | FDA-reported substance names retained as JSON. |
| `interaction_text` | Unmodified concatenated `drug_interactions` section text. |
| `source_url` | Canonical openFDA record URL. |
| `source_hash` | SHA-256 of the normalized source payload for audit/change detection. |
| `imported_at` | UTC timestamp at successful import. |

A database-level unique constraint on `(set_id, version)` makes imports
idempotent. PostgreSQL remains the source of truth; no database file or FDA
payload is committed to the repository.

## Import contract

The `import_fda_drug_labels` management command will:

1. Request only the fixed FDA HTTPS endpoint with a fixed query for the
   `drug_interactions` field; no user-provided URL is accepted.
2. Use bounded pagination, a request timeout, a bounded response size, and a
   small maximum retry policy for transient failures.
3. Validate the response structure and required fields before persistence.
4. Write each valid label-version atomically through Django's ORM.
5. Upsert matching `(set_id, version)` rows only when the source hash changed.
6. Print counts and identifiers only; it does not print raw label text or
   upstream response bodies.

An optional API key may be read only from an environment variable at runtime;
it is never committed, logged, or required for a basic import.

## Commands

```bash
(cd backend && uv run python manage.py makemigrations drug_labels)
(cd backend && uv run python manage.py migrate)
(cd backend && uv run python manage.py import_fda_drug_labels)
(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright && uv run pytest --cov=tests)
git diff --check
```

## Project structure

```text
backend/drug_labels/                     Django app and migration
backend/drug_labels/management/commands/ import command
backend/tests/drug_labels/               model and import-command tests
docs/decisions/                          durable decision record
```

## Code style

Use Django 5.2 ORM models and explicit constraints. Keep parsing separate
from persistence so source data can be validated before a database write.

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["set_id", "version"],
            name="drug_label_interaction_set_id_version_uniq",
        )
    ]
```

## Testing strategy

- Write failing tests before production code.
- Unit-test FDA-payload validation, including missing IDs, blank interaction
  text, and invalid data types.
- Test command pagination, idempotent re-import, changed-payload update,
  timeout/failure handling, and rejection of unexpected endpoint data using
  a fake HTTP transport.
- Run Django migrations and tests against PostgreSQL as part of the backend
  suite. No real FDA request is made in tests.

## Boundaries

- **Always:** preserve raw source text, use parameterized ORM writes, record
  provenance, enforce the unique constraint, set timeouts and response limits,
  test failure paths, and cite source/documentation.
- **Ask first:** a normalized interaction-pair model, clinical interpretation
  or severity labels, an API/UI, automatic sync, new external providers, or
  changes to the database/hosting architecture.
- **Never:** state or imply clinical completeness/safety, fetch a
  user-supplied URL, commit FDA payloads or credentials, log label bodies, or
  add authentication/product features as part of this import.

## Sources

- FDA openFDA Drug Label API: https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/
- FDA openFDA SPL dataset description: https://open.fda.gov/data/spl/
- Django 5.2 model constraints: https://docs.djangoproject.com/en/5.2/ref/models/constraints/
- Django management commands: https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/

## Open questions

None for the first import slice. FDA label text is retained as source material;
any clinical interpretation requires a separate, reviewed specification.
