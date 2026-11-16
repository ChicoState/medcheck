# Weekly medication organizer

Authenticated users can view a private, read-only weekly schedule beneath My Medication. Seven day buttons show the current week's dates. Choosing a day reveals medicine names, times, and food instructions. Empty days have an explicit message, and loading and service errors are shown in place.

The Django endpoint `GET /api/medications/schedule/` creates prototype doses on the first read for each account and returns the same stored rows thereafter. A saved medicine can be scheduled through its account-owned record. Real patient data is outside this prototype.

Verification: backend tests cover authentication, account isolation, and persistence; Playwright covers day selection, dose details, and reload; formatting, types, build, and existing tests must pass.

The visual treatment is a continuous seven-compartment sage pill case with translucent lids and decorative pill illustrations. The illustrations do not represent the physical appearance of named medicines. On narrow screens, the case scrolls horizontally with several compartments visible; the selected day's details remain below the case.

Saved medicines can be scheduled on selected Monday–Sunday days. A compact panel offers every-weekday and every-day shortcuts, morning/afternoon/evening options, and an editable time. The selected period supplies a default time unless the user has edited it. Saving replaces that medicine's prior schedule, updates the case, and removes prototype doses on the first real schedule save. Removing a schedule clears its doses. No food instruction is inferred from the saved product label.
