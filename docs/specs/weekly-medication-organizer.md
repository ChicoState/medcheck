# Weekly Medication Organizer Specification

## Objective

Add a weekly, pill-organizer-inspired schedule to the authenticated My
Medication page. A user can select any day to reveal the medicines scheduled
for that day, including the dose time and whether each medicine should be taken
with food.

The schedule is persisted per authenticated account through the Django API.
New accounts receive the current prototype schedule the first time the
organizer loads. Schedule editing is intentionally not part of this increment.

## Interaction and Accessibility

- Show seven day compartments in a responsive horizontal organizer.
- Each day is a keyboard-accessible button with its weekday and date.
- Selecting a day expands a details panel below the organizer.
- The details panel lists medicine name, time, and food instruction.
- The selected day is announced through `aria-pressed` and a visible heading.
- The empty-day state explains that no doses are scheduled.

## Testing Strategy

Playwright covers selecting a day and verifying the selected day’s medicine,
time, and food instruction. Backend tests cover authentication, persistence,
and account isolation. The live account browser test verifies the schedule is
still present after a reload.

## Boundaries

- Always keep the schedule local, responsive, and keyboard accessible.
- Ask before adding schedule editing, imports, integrations, or real medication
  data.
- Never store or log real patient or medication data in this prototype.

## Success Criteria

- Authenticated users see the organizer at the bottom of My Medication.
- Clicking a day reveals that day’s schedule details.
- The details include medication name, time, and food guidance.
- The organizer passes formatting, linting, type checking, unit tests, build,
  and browser tests.
