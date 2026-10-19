# Medication Search and Saved Library Specification

## Status

Implemented local MVP. This document records the first application slice that
turns the search prototype into a live medication search and saved-library
workflow. Public deployment still requires an API key, shared cache, and
reverse-proxy query-log redaction.

Implementation note: `sourceUrl` is derived from the fixed openFDA host and
validated `set_id` when serializing a label, rather than stored as a separate
database column. This avoids persisting a provider URL or credential-bearing
variant. The local development database remains SQLite by default;
`DATABASE_URL` selects PostgreSQL, which the backend CI job exercises.

## Objective

Visitors can search a live medication-information source and open a product
label. Authenticated users can save labels that interest them and review or
remove them later from My Medication.

Each result and saved item represents one product label, not a unique active
ingredient or a complete medication regimen. Different manufacturers,
strengths, and dosage forms may produce similar names. The first release is a
reference and discovery tool. It does not diagnose, prescribe, calculate a
dose, track adherence, or replace a clinician or pharmacist.

## Success criteria

- A visitor can search a medication name and open an attributed label from
  live openFDA data, including clear empty and unavailable states.
- A signed-in user can save a label once, find it after signing out and back
  in, reopen it, and remove it; another account cannot see or remove it.
- Automated checks cover provider failures, privacy boundaries, and the
  complete browser journey without depending on live openFDA availability.
- The same saved relationships survive on the approved PostgreSQL deployment
  path, and provider credentials stay server-side.

## Commands

Run these from the repository root after the new app and check configuration
are added. Until then, use the current commands in `AGENTS.md`:

```bash
(cd backend && uv run pytest --cov=accounts --cov=medications)
(cd backend && uv run ruff format --check . && uv run ruff check . && uv run pyright)
(cd backend && set -a && source ../.env.example && set +a && uv run python manage.py check)
(cd backend && uv run bandit --quiet --recursive accounts config medications)
(cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build)
(cd web && pnpm test:e2e)
git diff --check
```

For the manual live-provider check, start the project with `./scripts/dev.sh`
after supplying a local, untracked `OPENFDA_API_KEY`. The current development
database is SQLite; PostgreSQL application configuration and an integration
test path must be added before cross-device persistence can be claimed.

## Project structure

- `backend/medications/` — provider adapter, normalization, models, migrations,
  API views, and medication tests.
- `backend/tests/medications/` — provider fixtures, model tests, and API tests.
- `web/src/` — medication API client, typed contracts, search/detail/library
  components, routes, and styles.
- `web/tests/e2e/` — Playwright coverage for the medication flow. The current
  Jest setup checks tooling only; adding component tests requires an explicit
  test-runner and dependency change.
- `docs/specs/` — this specification and future provider/API decisions.

## Code style and interface conventions

Backend code should keep provider-specific parsing inside the adapter and
return typed normalized values to the application layer. Frontend code should
use the normalized camelCase API contract and keep loading/error/success states
explicit in the component state. For example:

```typescript
type MedicationSummary = {
  provider: string;
  externalId: string;
  displayName: string;
  genericName: string | null;
  isSaved: boolean;
};
```

Use the repository's Ruff, Prettier, ESLint, and TypeScript formatting rules;
avoid introducing a new abstraction until a second provider or second consumer
requires it.

## Boundaries

- **Always:** validate user input and provider responses, derive ownership from
  the session, keep provider credentials server-side, use CSRF-protected
  mutations, escape provider content, and run the relevant tests before each
  implementation increment.
- **Ask first:** add a second provider, add personal regimen or note fields,
  or change authentication or CSRF behavior.
- **Never:** commit secrets, expose API keys to JavaScript, log medication
  queries or full labels, render untrusted provider HTML, or present provider
  content as personalized medical advice.

## MVP scope

### Included

- Medication-name search against a live external provider.
- Product-label results with stable external identifiers and concise summaries.
- Medication detail pages with normalized label sections and source metadata.
- Authenticated save, list, and remove operations.
- A private My Medication page that persists across sessions locally and across
  devices once the planned hosted PostgreSQL configuration is in place.
- Provider failures, empty results, loading states, and stale-cache messaging.
- Automated backend, frontend, and browser coverage without requiring live
  provider calls in CI.

### Not included

- User-entered dose, schedule, condition, adherence, or symptom data.
- Medication interaction checking or personalized medical advice.
- Full-text medical search across symptoms or health topics.
- Browser-to-provider requests, client-exposed provider credentials, or
  storing the provider's unfiltered raw response.
- Multiple external providers in the first implementation.

## Provider decision

### Initial provider: openFDA Drug Labeling API

Use `https://api.fda.gov/drug/label.json` through a server-side Django
adapter. The label endpoint supports searchable drug-label fields and returns
prescription and OTC product labeling, including sections such as indications,
warnings, contraindications, adverse reactions, and dosage information. The
provider documents `set_id` as a stable identifier for a label across
revisions; store it as the external label identity. Store `rxcui`
when supplied, but do not require it because it is not guaranteed on every
record.

The adapter must normalize provider responses into a MedCheck-owned contract.
The rest of the application must not depend on openFDA field names or nested
arrays.

### Provider boundary

Keep the provider-specific HTTP and parsing code in one backend module with
small `search_labels` and `get_label` functions returning normalized values.
Introduce a formal provider protocol only when another provider is added.
The callable contract is equivalent to:

```python
def search_labels(query: str, *, page: int, page_size: int) -> SearchPage: ...

def get_label(external_id: str) -> MedicationDetails: ...
```

Use the fixed `https://api.fda.gov/drug/label.json` host, a short request
timeout, and `OPENFDA_API_KEY`. A key is optional for a local trial but is
required before public deployment. openFDA's endpoint guide permits trial
calls without a key while its authentication page says a key is required and
publishes lower no-key limits; verify local trial behavior in Task 1. Send a
configured key using the documented Authorization header, never to the browser
or logs. Start with Python's standard-library HTTP client; add a dependency
only if the live probe or tests show it is necessary.

Search only `openfda.brand_name` and `openfda.generic_name` initially. Those
harmonized fields can be absent, so records without a usable name may not
appear; explain this coverage limit in the UI. Escape the complete user term
inside the provider's query syntax before URL encoding; test quotes, colons,
operators, and whitespace. Detail lookup uses an exact `set_id` search and
selects the latest revision if more than one is returned, not an arbitrary
user-supplied URL. Forbid redirects to unexpected hosts.

### Data-use guardrails

openFDA states that its data is not validated for medical-care decisions and
may differ from currently distributed or approved labeling. Show FDA/openFDA
attribution, a source link, the label's `effective_time` and the dataset's
`meta.last_updated` separately when available, and a plain-language reminder
to consult a qualified healthcare professional. Render provider text as
escaped plain text; never render provider HTML directly.

## Domain model

Use two Django models in a new `medications` application:

### `Medication`

The normalized, refreshable cache of one provider record.

- `provider` — short identifier, initially `openfda`.
- `external_id` — provider identifier, initially `set_id`.
- `rxcui` — nullable normalized RxNorm identifier when present.
- `display_name` — canonical label/product name.
- `generic_name` — nullable.
- `brand_names` — normalized list.
- `active_ingredients` — normalized list.
- `dosage_forms` and `routes` — normalized lists.
- `label_sections` — allowlisted structured sections represented as plain text.
- `label_effective_date` — nullable label `effective_time` date.
- `dataset_updated_at` — nullable dataset `meta.last_updated` date.
- `fetched_at` — last successful fetch time.
- `source_url` — provider/source link where available.
- `created_at` and `updated_at`.

Add a unique constraint on `(provider, external_id)`. That constraint supplies
the lookup index; add name indexes only if a measured local query needs them.
Do not store the complete raw provider response.
Construct source links from the fixed provider host and validated `set_id`;
never persist or return a credential-bearing request URL.

### `SavedMedication`

The private relationship between an account and a medication.

- `user` — foreign key to Django's authenticated user.
- `medication` — foreign key to `Medication`.
- `saved_at`.

Add a unique constraint on `(user, medication)` so saving is idempotent. The
user is always taken from `request.user`; no endpoint accepts a client-supplied
user id.

## API contract

Search and detail endpoints are under `/api/medications/`; private collection
endpoints are under `/api/saved-medications/`. Search and detail are available
without authentication. Save, list, and remove require an authenticated
session; save and remove also require the existing Django CSRF token. New
medication endpoints use `{ "error": { "code": "...", "message": "..." } }`
for failures. The existing `/api/auth/` error contract remains unchanged.
Use `400` for invalid inputs, `401` for missing session, `404` for absent
labels or user-owned saves, `429` for MedCheck throttling, `502` for invalid
upstream responses, and `503` for provider timeout, rate limit, or outage.
Never return upstream bodies or credential-bearing URLs.

### Search

`GET /api/medications/?q=ibuprofen&page=1&pageSize=20`

Response shape:

```json
{
  "data": [
    {
      "provider": "openfda",
      "externalId": "...",
      "displayName": "...",
      "genericName": null,
      "brandNames": ["..."],
      "dosageForms": ["..."],
      "routes": ["..."],
      "rxcui": null,
      "isSaved": false
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "hasNextPage": true
  }
}
```

Rules:

- Trim and validate `q` (1–100 characters), `page` (positive integer), and
  `pageSize` (1–20, default 20); invalid values never call the provider.
- Search uses provider `limit` and `skip=(page-1)*pageSize`. Reject pages whose
  skip would exceed openFDA's documented 25,000 limit. Return one result per
  matching label record; do not deduplicate or claim a unique-medication total.
  `hasNextPage` comes from provider result metadata and the reachable skip
  range. A short page is allowed if invalid records are omitted.
- Return `{ "data": [], "pagination": { "page": 1, "pageSize": 20,
  "hasNextPage": false } }` for no matches, including openFDA's no-result
  response.
- `isSaved` is always boolean; it is `false` for signed-out visitors and is
  computed from the session user's saves for signed-in visitors.
- Do not log the raw query because medication searches can be sensitive.
- Redact the `q` parameter from Django, reverse-proxy, and error-tracing
  request logs; the browser's `/search?q=...` URL remains visible in its local
  history by design.

### Detail

`GET /api/medications/{provider}/{externalId}/`

Return the normalized summary fields from search plus
`sections: [{ "key": "warnings", "title": "Warnings", "text": "..." }]`,
`labelEffectiveDate`, `datasetUpdatedAt`, `fetchedAt`, `isStale`,
`sourceUrl`, and `disclaimer`. Dates are ISO 8601 or `null`; absent optional
sections are omitted from the array. `sourceUrl` is built without an API key.
Select the newest revision by numeric `version`, then `effective_time`; reject
any result with a different `set_id`. Fresh cached detail (under 24 hours old)
is served without an upstream call. Expired detail triggers refresh; if that
fails, return the cached detail with `isStale: true` and its original
`fetchedAt`. A missing label with no cache is `404`; provider failure with no
cache uses the safe error mapping above. `isSaved` is `false` for visitors.

### Saved medications

`GET /api/saved-medications/`

Returns the authenticated user's saved labels, ordered newest first with a
stable id tie-breaker, paged with the same 1–20 limit. Each item includes
`savedId`, `savedAt`, the normalized summary, `labelEffectiveDate`, `fetchedAt`,
and `isStale` (older than 24 hours). Listing uses stored records and never
blocks on openFDA; it does not automatically refresh every saved label. The
response uses `{ "data": [/* saved items */], "pagination": { "page": 1,
"pageSize": 20, "hasNextPage": false } }`.

`POST /api/saved-medications/`

Request:

```json
{
  "provider": "openfda",
  "externalId": "..."
}
```

The backend accepts only `provider: "openfda"` and a UUID-shaped `externalId`,
fetches or refreshes the matching label when necessary, and creates or returns
the existing relationship. New save returns `201` and
`{ "savedId": 1, "created": true }`; duplicate save returns `200` and
`{ "savedId": 1, "created": false }`. Both return the same relationship id.
Enforce idempotence at the database constraint as well as in the view.

`DELETE /api/saved-medications/{savedId}/`

Deletes only a relationship owned by the authenticated user and returns `204`.
Missing and other-user ids both return `404`.

## Web experience

### Routes

- `/` — medication search form.
- `/search?q=...` — search results with pagination or load-more behavior.
- `/medications/:provider/:externalId` — medication detail.
- `/my-medication` — authenticated saved-medication list.
- `/saved-medicines` — preserve the existing redirect to `/my-medication`.

### Required states

- Search form: empty, submitting, results, no results, invalid query, and
  provider unavailable.
- Detail page: loading, loaded, not found, unavailable, save pending, saved,
  and save failure.
- My Medication: loading, empty, populated, stale-label notice, and remove
  confirmation/error. Listing is database-backed and does not refresh labels.
- Signed-out save attempt: explain that an account is required and provide the
  existing sign-in flow. Hoist a small account-popover opener from Navigation
  into App so the detail page can open it. After sign-in, stay on the detail
  page and require an explicit Save click; do not silently save.

Search UI copy must say results are drug product labels and may include
similar names or omit products without searchable name annotations. Replace
the current placeholder promising symptom and health-topic search with a
medication-name prompt. Keep the existing `/saved-medicines` redirect and
logged-out `/my-medication` redirect.

Use accessible headings, semantic lists, keyboard-visible controls, live status
messages for asynchronous changes, and responsive layouts down to 320px.

## Security, privacy, and reliability

- Keep all external calls in Django; never call openFDA directly from React.
- Read provider credentials from environment configuration only.
- Use the fixed HTTPS provider host, bounded timeouts and response-size limits;
  at most one retry for transient read failures, never for invalid responses.
- Validate both user query input and every provider response before use.
- Allowlist provider names, detail fields, and label sections.
- Escape or sanitize provider text before rendering.
- Enforce session authentication and CSRF on save/delete.
- Enforce ownership on every saved-medication query and mutation.
- Add bounded search throttling and a five-minute cache for identical
  normalized queries before the search UI is connected. Use a shared cache
  backend for multiworker deployment; local memory cache is only a local
  development fallback. This is quota protection, not an authorization check.
- Do not log query text, API keys, full label bodies, session cookies, or saved
  medication contents. Redact query parameters in access logs and traces. Log
  only provider name, operation, status category, latency, and a non-sensitive
  request identifier.
- Document that saved medications are personal health-related data and add a
  deletion path for saved relationships.

## Testing strategy

### Backend

- Provider adapter unit tests use fixed JSON fixtures for valid, empty,
  malformed, 404, 429, timeout, redirects, oversized responses, and 5xx.
- Normalization tests verify missing optional fields, duplicate arrays, text
  cleanup, stable IDs, and rejection of invalid records.
- API tests cover query escaping, validation, page bounds, error mapping,
  search throttle, cache freshness, authentication, CSRF, duplicate saves,
  ownership isolation, list ordering, and deletion.
- Reconfigure backend coverage and Pyright to include `medications`, not only
  `tests`; change CI's pytest coverage targets and Bandit scan to include
  `medications`.
- Add an isolated real Django/database browser check for save → reload → list
  → sign out/in → list → remove. Keep provider HTTP mocked at the Django
  boundary; do not rely on the live provider to prove persistence. Add a
  PostgreSQL integration path when PostgreSQL app configuration lands.

### Web

- Playwright covers search states, detail rendering, save state, empty
  library, provider errors, and an authenticated search → detail → save → My
  Medication → remove journey with deterministic API responses. Keep UI
  verification in Playwright for this slice; the current Jest configuration
  runs infrastructure tests only.
- No CI test should depend on openFDA availability or consume the shared API
  key.

### Manual integration check

With `OPENFDA_API_KEY` configured locally, run the backend and verify real
queries for a generic and a brand name, label detail lookup by `set_id`, a
save, and a later review. Inspect whether searches return multiple revisions
or multiple products per label. Record the result shapes in synthetic fixtures
and the response date, without storing personal search terms or credentials.

## Implementation plan

### Phase 1: Contract and provider foundation

#### Task 1: Probe the live provider and freeze the contract

**Acceptance criteria:**

- [ ] With a local key, probe a generic name, a brand name, and exact `set_id`
      lookup; inspect missing harmonized fields, revisions, result metadata,
      and no-result behavior. Record sanitized fixture shapes.
- [ ] Confirm the exact provider query syntax, response size, auth header,
      timeout, search page cap, and fallback assumptions in this contract.
- [ ] FDA/openFDA attribution and medical-information copy are agreed.

**Verification:** Read-only live probe succeeds; check fixtures against the
official fields and API docs. If the result identity differs from the spec,
revise the spec before building the schema.

**Dependencies:** None.

**Likely files:** this spec and redacted test fixtures.

**Scope:** Small.

#### Task 2: Add the medications Django app and schema

**Acceptance criteria:**

- [ ] `Medication` and `SavedMedication` models, constraints, indexes, and
      migrations exist.
- [ ] The app is registered without changing account behavior.
- [ ] Model tests prove duplicate prevention and user isolation at the query
      boundary.
- [ ] Backend coverage, Pyright, and CI pytest configuration include the new
      app so later checks measure application code.

**Verification:** Django checks, migrations check, model tests, and existing
      account tests pass on the current local SQLite path.

**Dependencies:** Task 1.

**Likely files:** `backend/medications/**`, settings, URL configuration, and
      backend tests.

**Scope:** Medium.

### Checkpoint: Foundation

- [ ] Contract fixtures are agreed.
- [ ] Migrations apply cleanly.
- [ ] Existing backend and web checks remain green.

### Phase 2: Live search vertical slice

#### Task 3: Implement and test the openFDA provider adapter

**Acceptance criteria:**

- [ ] Search and detail calls use the fixed HTTPS host, timeout, and optional
      local API key; redirects and oversized responses fail safely.
- [ ] Responses are validated and normalized into MedCheck types.
- [ ] Upstream statuses and malformed data map to safe internal errors.
- [ ] No raw provider payload or secret is logged.

**Verification:** Provider fixture tests for success and all failure classes;
      static analysis and type checks pass.

**Dependencies:** Tasks 1–2.

**Likely files:** provider module, normalization types, backend tests, and
      backend settings.

**Scope:** Medium.

#### Task 4: Expose the medication search endpoint

**Acceptance criteria:**

- [ ] Valid queries return the stable MedCheck response shape and bounded
      pagination.
- [ ] Empty or invalid queries never reach the provider.
- [ ] Provider failures return safe, documented status/error responses.
- [ ] Five-minute query caching, conservative search throttling, and query
      redaction in application logs are in place before public search is
      exposed.

**Verification:** Django API tests including request validation and mocked
      provider calls.

**Dependencies:** Task 3.

**Likely files:** medications views/URLs, backend API tests, and cache settings.

**Scope:** Medium.

#### Task 5a: Add typed web API client for search

**Acceptance criteria:**

- [ ] The client parses the normalized success/error contract and uses only
      same-origin `/api` requests.
- [ ] Search can be requested by query and page without provider-specific
      field names or client-side secrets.

**Verification:** Type check plus Playwright route mock proving request URL and
      response/error handling.

**Dependencies:** Task 4.

**Likely files:** web medication API/types module and browser tests.

**Scope:** Small.

#### Task 5b: Connect the Home search UI to live search results

**Acceptance criteria:**

- [ ] The search form navigates to `/search?q=...` and renders results,
      loading, empty, and error states.
- [ ] Result cards link to detail routes using provider and external ID.
- [ ] Existing account/navigation behavior and accessibility remain intact.

**Verification:** Formatting/lint/type/build checks and a Playwright search
      journey with mocked API responses; update the prototype's old echo test.

**Dependencies:** Task 5a.

**Likely files:** `web/src/App.tsx`, focused search component, styles, and
      browser tests.

**Scope:** Medium.

### Checkpoint: Search slice

- [ ] A user can submit a medication search and see linked label results.
- [ ] No browser request contains the provider API key.
- [ ] Existing landing-page and account tests pass.

### Phase 3: Detail and save vertical slice

#### Task 6: Add detail lookup and normalized cache refresh

**Acceptance criteria:**

- [ ] Detail requests validate provider/external ID and upsert the normalized
      medication cache.
- [ ] The response includes only allowlisted fields and source/disclaimer data.
- [ ] A provider outage can return a safe cached representation when one exists.

**Verification:** API tests for first fetch, refresh, cache fallback, 404, and
      malformed upstream data.

**Dependencies:** Tasks 2–4.

**Likely files:** provider/service/model logic, detail view/serializer, tests.

**Scope:** Medium.

#### Task 7: Add save/list/remove API operations

**Acceptance criteria:**

- [ ] Save requires authentication and CSRF, validates the external record,
      and is idempotent.
- [ ] List returns only the current user's stored records, newest first, with
      bounded pagination and no provider call.
- [ ] Delete cannot affect or reveal another user's saved record.

**Verification:** Authenticated and unauthenticated API tests, ownership tests,
      CSRF tests, and duplicate-save tests.

**Dependencies:** Task 6.

**Likely files:** saved-medication views/URLs/serializers, model tests, API
      tests, auth client helper if needed.

**Scope:** Medium.

#### Task 8: Build medication detail and save interaction

**Acceptance criteria:**

- [ ] Detail page renders normalized sections, source attribution, disclaimer,
      and current saved state.
- [ ] Authenticated users can save and see confirmation without a full reload.
- [ ] Signed-out users can open the existing account popover; after sign-in,
      they remain on the detail page and explicitly click Save.

**Verification:** Playwright detail/save journey with a
      mocked backend.

**Dependencies:** Tasks 5b–7.

**Likely files:** detail components, web API client/types, styles, tests.

**Scope:** Medium.

### Phase 4: Review and hardening

#### Task 9: Replace the empty My Medication page with the saved library

**Acceptance criteria:**

- [ ] Authenticated users see their saved medications across reloads.
- [ ] Each item can reopen its detail page and can be removed safely.
- [ ] Empty, loading, and stale-cache states are clear and accessible.

**Verification:** Full Playwright search → save → review →
      remove flow.

**Dependencies:** Task 8.

**Likely files:** `web/src/App.tsx` or split route components, API client,
      styles, E2E tests.

**Scope:** Medium.

#### Task 10: Wire PostgreSQL and real persistence verification

**Acceptance criteria:**

- [ ] Backend database settings can use the approved PostgreSQL deployment
      path while local SQLite remains available.
- [ ] An isolated integration test proves save → reload/sign-in → list →
      remove against real Django/database state.
- [ ] PostgreSQL migrations and that integration path run in CI or an explicit
      required pre-merge check.

**Verification:** Migration and persistence checks pass on PostgreSQL;
      database configuration is documented without secrets.

**Dependencies:** Tasks 2 and 7–9.

**Likely files:** settings, persistence tests, CI workflow, and environment
      example.

**Scope:** Medium.

#### Task 11: Finish verification and documentation

**Acceptance criteria:**

- [ ] CI Bandit scans `medications`, and provider status/latency are observable
      without sensitive content.
- [ ] README, AGENTS.md, setup instructions, and this spec match implemented
      paths, commands, provider limits, and disclaimer wording.
- [ ] Manual live-provider check passes with a key; automated CI does not call
      openFDA. A reviewer checks ownership and upstream data handling.

**Verification:** Full backend/web checks, build, Playwright, PostgreSQL
      integration, security checks, and `git diff --check`.

**Dependencies:** Tasks 1–10.

**Likely files:** backend tool configuration, CI workflow, README, AGENTS.md,
      and this spec.

**Scope:** Medium.

### Checkpoint: Complete

- [ ] Search, detail, save, review, and remove work end-to-end.
- [ ] User data is private and provider credentials are server-only.
- [ ] Provider failure behavior is safe and tested.
- [ ] Full backend, web, build, and browser verification passes.
- [ ] A code review covers authorization, data minimization, and external API
      handling before merge.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| openFDA label records are inconsistent or similar | Medium | Normalize allowlisted fields, show label-specific names, test missing fields, and avoid claiming unique medications. |
| Provider quota or outage | High | Server-side key, short cache, bounded page size, rate limiting, timeout, and cached detail fallback. |
| Users interpret labels as personalized medical advice | High | Persistent source attribution, disclaimer, no personalized recommendations, and clear product scope. |
| Provider content contains unsafe markup or unexpected data | High | Validate response shape, store normalized plain text, and escape/sanitize before rendering. |
| Medication saves leak between accounts | High | Ownership derived from session user, unique relationship constraint, and cross-user API tests. |
| External contract changes | Medium | Adapter boundary, provider fixtures, versioned MedCheck contract, and documented provider metadata. |

## Future decisions and deployment prerequisites

- Provision an openFDA API key before public deployment; this is an external
  credential setup step, not a blocker for deterministic implementation work.
- Initial sections are purpose/indications, warnings, contraindications,
  adverse reactions, dosage/administration, and patient information when
  available. Omit absent sections without implying the information is absent
  from all labels.
- Confirm whether a later phase should add RxNorm as a second source for
  normalized name search and cross-provider identity.
- Confirm whether users eventually need personal notes or regimen fields;
  keep them out of this MVP so the saved-library model remains reference-only.

## Official references

- [openFDA Drug Labeling: how to use the endpoint](https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/)
- [openFDA Drug Labeling: searchable fields](https://open.fda.gov/apis/drug/label/searchable-fields/)
- [openFDA Drug Labeling: field definitions, including `set_id`](https://open.fda.gov/fields/druglabel_reference.pdf)
- [openFDA API authentication and rate limits](https://open.fda.gov/apis/authentication/)
- [openFDA API paging](https://open.fda.gov/apis/paging/)
- [openFDA drug labeling overview and responsible-use disclaimer](https://open.fda.gov/apis/drug/label/)
- [NLM RxNorm API documentation](https://www.lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html)
