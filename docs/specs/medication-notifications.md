# Medication Notifications Specification

## Objective

Give an authenticated user opt-in email notifications for medication doses,
vitamin doses, and prescription refills. Notifications are account-owned and
must not expose one user's schedule or refill information to another user.

## Behavior

- A user can enable or disable dose reminders, vitamin reminders, and refill
  reminders independently.
- Dose and vitamin reminders are sent one hour before a dose in the user's
  weekly schedule.
- A user can record a medication name and the date its refill is due. Refill
  reminders are sent seven days before the due date by default.
- A scheduled delivery run is idempotent: retrying the same run does not send
  duplicate email for the same account, notification type, item, and target
  time.
- Notification email contains only the minimum necessary medication name,
  scheduled time, or refill date. No provider label text is included.
- All notification APIs require session authentication and CSRF protection for
  writes.

## API contract

- `GET /api/notifications/settings/` returns the account's notification
  settings, creating safe opt-in defaults on first read.
- `PATCH /api/notifications/settings/` accepts `doseReminders`,
  `vitaminReminders`, and `refillReminders` booleans.
- `GET /api/notifications/refills/` lists the account's refill records.
- `POST /api/notifications/refills/` creates `{name, dueDate}`.
- `DELETE /api/notifications/refills/:id/` removes an account-owned refill.

## Delivery

`python manage.py send_medication_notifications` sends due notifications for
the current minute. It is intended to be invoked by cron or the deployment's
scheduled-job facility every minute. SMTP or another Django email backend must
be configured outside the repository; development uses the locmem backend in
tests.

## Safety and boundaries

- This is a reminder service, not a clinical decision system. The UI and email
  state that users should follow their clinician's instructions.
- Refill dates are reminders only and do not confirm that a prescription can be
  refilled.
- No real patient data belongs in local fixtures, tests, logs, or email
  snapshots.

## Success criteria

- Backend tests prove ownership, validation, idempotent email delivery, and all
  three notification categories.
- An authenticated user can configure the preferences and refill dates from My
  Medication.
- Existing schedule, account, and web test suites continue to pass.
