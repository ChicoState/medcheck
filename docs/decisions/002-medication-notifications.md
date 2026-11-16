# ADR-002: Scheduled email delivery for medication notifications

## Status

Accepted

## Context

MedCheck already stores account-owned weekly medication doses, but has no
delivery mechanism for reminders. Dose reminders, vitamins, and refill dates
are private account data. The current infrastructure plan does not select a
task queue or background-worker service.

## Decision

Store notification preferences, refill dates, and delivery records in Django's
relational database. Send due emails from a Django management command that can
be run every minute by cron or a hosting provider's scheduled job. Use a
delivery record with a uniqueness constraint to make retries idempotent.

## Alternatives considered

### Add Celery and Redis

Rejected for this increment because it expands the infrastructure plan with a
new always-on service before a hosting provider has been selected.

### Browser timers

Rejected because browsers cannot reliably deliver reminders when closed and
would not support cross-device behavior.

### Provider-supplied refill data

Rejected because product labels do not contain a user's prescription quantity,
fill date, or pharmacy refill status. Users must provide the due date.

## Consequences

- Production must configure a secure Django email backend and a scheduled job.
- Notification delivery is at-least-once at the job boundary and exactly-once
  per stored delivery key.
- The server timezone is the source of truth for this first increment; a
  per-user timezone can be added when the account profile supports it.
