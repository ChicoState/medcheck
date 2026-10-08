# Saved Medicines Navigation Specification

## Objective

Add sliding navigation to the MedCheck prototype so a user can move between
the existing Home page and, when authenticated, a dedicated Saved Medicines
page. The Saved Medicines page must clearly represent the current no-data state
and provide a list layout that can render medicine records when a future data
source exists.

This feature does not add a save action, authentication, browser persistence,
a backend API, or a medicine domain model.

## Routes and Navigation

- `/` renders the existing MedCheck search prototype.
- `/saved-medicines` renders the Saved Medicines page.
- After account integration, `/my-medication` is the primary route and
  `/saved-medicines` redirects to it. The menu label is My Medication.
- The hamburger button opens a full-height drawer that slides in from the left.
- The drawer begins beneath the hamburger control and places a backdrop over
  the remaining page.
- The drawer always contains Home and only contains Saved Medicines when the
  user is authenticated.
- Following a link closes the popover.
- Pressing Escape or the backdrop closes the drawer. Escape returns focus to
  the hamburger button.
- The current destination is identified with `aria-current="page"`.
- Logged-out users who load `/saved-medicines` directly are redirected Home.

## Saved Medicines States

- With no supplied medicines, show the heading `Saved Medicines` and the
  message `No saved medicines yet.`
- When medicine records are supplied in the future, render their names in a
  semantic list.
- Do not seed fake medicines or imply that data survives a reload.

## Testing Strategy

Playwright covers menu interaction, keyboard dismissal, navigation, direct
route loading, active-page state, and the Saved Medicines empty state. Existing
landing-page search behavior remains covered by its current tests.

## Boundaries

- Always keep navigation keyboard-accessible and responsive down to 320px.
- Ask before adding persistence, authentication, APIs, or medical-data sources.
- Never store or log real medicine or account data in this prototype.

## Success Criteria

- Home is always reachable from the hamburger menu.
- Saved Medicines is only visible and reachable for authenticated users.
- Authenticated visits to `/saved-medicines` display a meaningful empty state.
- Menu state and focus behavior are accessible by keyboard.
- Formatting, linting, type checking, tests, build, and browser tests pass.
