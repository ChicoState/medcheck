import {
  expect as playwrightExpect,
  test as playwrightTest,
} from "@playwright/test";

export const test = playwrightTest.extend({
  page: async ({ page }, use) => {
    // E2E tests mock the API calls relevant to each scenario. Keep unrelated
    // app-startup requests local to the browser suite so they do not depend on
    // a Django process running on port 8000.
    await page.route("**/api/auth/me/", (route) =>
      route.fulfill({ status: 401, json: {} }),
    );
    await page.route("**/api/medications/schedule/", (route) =>
      route.fulfill({
        json: {
          schedule: {
            Monday: [],
            Tuesday: [],
            Wednesday: [],
            Thursday: [],
            Friday: [],
            Saturday: [],
            Sunday: [],
          },
        },
      }),
    );
    await use(page);
  },
});

export const expect = playwrightExpect;
