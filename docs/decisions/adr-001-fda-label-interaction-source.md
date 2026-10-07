# ADR-001: Preserve FDA label interaction text without clinical normalization

## Status

Accepted — 2026-09-30.

## Date

2026-09-30

## Context

Medcheck needs an authoritative starting point for drug-interaction-related
data. FDA's openFDA Drug Labeling endpoint exposes the `drug_interactions`
section of submitted Structured Product Labeling records. The section is
heterogeneous free text and may vary by product and label version.

The approved infrastructure plan already selects Django and PostgreSQL as the
application's backend and source-of-truth database. A repository SQLite file
would diverge from that model and would be hard to update and audit.

## Decision

Create a Django/PostgreSQL `drug_labels` application that stores raw FDA
`drug_interactions` text per SPL label version, with source identifiers,
effective date, a canonical source URL, and a payload hash. Populate it only
through an explicit, bounded management-command import from the fixed FDA
openFDA endpoint.

The imported data is source material. It does not encode drug-pair assertions,
severity, mechanism, contraindications, or patient-specific advice.

## Alternatives considered

### Checked-in SQLite database

- Pros: Simple distribution and offline inspection.
- Cons: Conflicts with PostgreSQL as the source of truth; easily becomes stale;
  makes provenance updates and controlled migrations harder.
- Rejected.

### Normalized drug-pair interaction table

- Pros: Directly queryable for an interaction checker.
- Cons: FDA label text does not provide a complete, uniform, clinically
  reviewed pairwise schema. Automated extraction could create unsafe claims.
- Deferred to a separately reviewed clinical-data specification.

### FDA label text fetched at user request

- Pros: No local data import.
- Cons: Puts an external dependency on the product path, complicates
  availability and rate limits, and expands the server-side request surface.
- Rejected for this slice.

## Consequences

- Operators must run an import to refresh data; there is no automatic sync.
- Each stored row remains traceable to an FDA label version.
- Future user-facing or clinical interpretation features require their own
  specification, source policy, and safety review.

## References

- https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/
- https://open.fda.gov/data/spl/
