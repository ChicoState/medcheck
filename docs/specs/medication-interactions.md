# Medication Interaction Checking Specification

## Status

Implemented as a label-screening MVP on the `medication-interaction-checker`
branch. This feature does not provide a complete clinical drug-drug interaction
database and must not describe an absent label match as proof of safety.

## Objective

Allow a visitor to select two exact product labels by brand or generic name and
see whether either product's current openFDA label names the other product or
its normalized names in the label's `drug_interactions` section.

The feature is a reference and discovery tool. It does not replace a pharmacist
or clinician and does not provide personalized medical advice.

## Contract

`POST /api/interactions/check/` accepts exactly two existing openFDA label IDs:

```json
{
  "medications": [
    {"provider": "openfda", "externalId": "..."},
    {"provider": "openfda", "externalId": "..."}
  ]
}
```

The response includes both selected products, zero or more directional label
findings, the source URL for each finding, and a disclaimer. A finding means
only that the target product name or ingredient was found in the source label's
interaction text. An empty finding list means no match was found in the two
retrieved labels, not that the products are safe to combine.

## Boundaries

- Always keep provider calls server-side, validate both IDs and provider names,
  cap request body size, and render provider content as text.
- Always expose label effective dates, dataset freshness, and source links.
- Never infer severity, dose changes, or safety from raw text.
- Never log medication names, label bodies, or request payloads.
- A future licensed clinical DDI provider may be added behind the same service
  boundary; it requires a separate specification and licensing decision.

## Testing strategy

- Unit tests cover interaction-term extraction and directional matching.
- API tests cover valid matches, empty matches, malformed input, missing labels,
  and provider failures.
- Browser tests cover selecting a second product and displaying the result.

## Verification commands

```bash
(cd backend && uv run pytest tests/medications)
(cd web && pnpm format:check && pnpm lint && pnpm typecheck && pnpm test)
(cd web && pnpm build)
git diff --check
```
