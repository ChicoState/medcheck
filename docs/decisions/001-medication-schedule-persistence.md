# ADR-001: Persist medication schedules per account

## Status

Accepted

## Context

The weekly organizer initially rendered a local sample schedule in React. That
made the schedule disappear outside the browser prototype and gave every user
the same client-owned data. Medication schedules are private account data and
must survive page reloads while remaining isolated between users.

## Decision

Store one `MedicationSchedule` row per authenticated user and one
`MedicationDose` row for each scheduled medicine. The Django API exposes an
authenticated `GET /api/medications/schedule/` endpoint. The first read for a
new account creates the existing prototype schedule in that account's rows;
subsequent reads return the stored rows.

The React organizer is a read-only consumer for this increment. Schedule
editing will use the same account-owned records when its interaction is
specified.

## Alternatives considered

### Browser local storage

Rejected because it is device-local, bypasses account privacy boundaries, and
does not support cross-device use.

### One JSON field on the user

Rejected because individual doses need relational ownership, validation, and a
clear path to future editing and querying.

### Shared global schedule

Rejected because medication data must remain private to the authenticated user.

## Consequences

- Django migrations are required for local and hosted databases.
- The API is session-authenticated and read-only in this increment.
- New accounts receive the prototype schedule on first schedule read.
- Future create/update/delete endpoints must preserve the user ownership
  boundary and validate medication input.
