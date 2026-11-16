import { expect, test } from "@playwright/test";

const id = "00653b7c-7099-487e-9a01-e89781c21323";
const medicine = {
  provider: "openfda",
  externalId: id,
  displayName: "Ibuprofen Dye Free",
  genericName: "IBUPROFEN",
  brandNames: ["Ibuprofen Dye Free"],
  activeIngredients: ["Ibuprofen 200 mg"],
  dosageForms: [],
  routes: ["ORAL"],
  rxcui: null,
};
const pagination = { page: 1, pageSize: 20, hasNextPage: false };

test("search, inspect, sign in, save, review, and remove a label", async ({
  page,
}) => {
  let signedIn = false;
  let saved = false;
  let schedulePlan: { days: number[]; period: string; time: string } | null =
    null;
  const user = {
    id: 1,
    email: "member@example.com",
    username: "member@example.com",
  };
  await page.route("**/api/auth/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("csrf/"))
      return route.fulfill({ json: { csrfToken: "token" } });
    if (path.endsWith("me/"))
      return route.fulfill({
        status: signedIn ? 200 : 401,
        json: signedIn ? { user } : {},
      });
    if (path.endsWith("logout/")) {
      signedIn = false;
      return route.fulfill({ json: { ok: true } });
    }
    signedIn = true;
    return route.fulfill({ json: { user } });
  });
  await page.route("**/api/medications/?**", (route) =>
    route.fulfill({
      json: {
        data: [{ ...medicine, isSaved: saved }],
        pagination,
      },
    }),
  );
  await page.route(`**/api/medications/openfda/${id}/`, (route) =>
    route.fulfill({
      json: {
        ...medicine,
        isSaved: saved,
        sections: [
          {
            key: "warnings",
            title: "Warnings",
            text: "Ask a doctor. <script>not markup</script>",
          },
        ],
        labelEffectiveDate: "2026-04-29",
        datasetUpdatedAt: "2026-10-16",
        fetchedAt: "2026-10-19T00:00:00Z",
        isStale: false,
        sourceUrl: `https://api.fda.gov/drug/label.json?search=set_id%3A%22${id}%22`,
        disclaimer:
          "This is product-label information, not personal medical advice.",
      },
    }),
  );
  await page.route("**/api/saved-medications/**", (route) => {
    const method = route.request().method();
    const path = new URL(route.request().url()).pathname;
    if (method === "POST") {
      expect(route.request().headers()["x-csrftoken"]).toBe("token");
      saved = true;
      return route.fulfill({
        status: 201,
        json: { savedId: 1, created: true },
      });
    }
    if (method === "DELETE") {
      expect(route.request().headers()["x-csrftoken"]).toBe("token");
      saved = false;
      return route.fulfill({ status: 204, body: "" });
    }
    expect(path).toBe("/api/saved-medications/");
    return route.fulfill({
      json: {
        data: saved
          ? [
              {
                ...medicine,
                savedId: 1,
                savedAt: "2026-10-19T00:00:00Z",
                labelEffectiveDate: "2026-04-29",
                isStale: false,
                schedulePlan,
              },
            ]
          : [],
        pagination,
      },
    });
  });
  await page.route("**/api/saved-medications/interactions/", (route) =>
    route.fulfill({
      json: {
        status: "incomplete",
        pairsChecked: 0,
        totalPairs: 0,
        matches: [],
        reason: "need_two",
      },
    }),
  );
  await page.route("**/api/medications/schedule/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/1/")) {
      if (route.request().method() === "DELETE") {
        schedulePlan = null;
        return route.fulfill({ status: 204, body: "" });
      }
      schedulePlan = route.request().postDataJSON();
      return route.fulfill({ json: schedulePlan });
    }
    const names = [
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
    ];
    return route.fulfill({
      json: {
        schedule: Object.fromEntries(
          names.map((name, day) => [
            name,
            schedulePlan?.days.includes(day)
              ? [
                  {
                    id: day + 1,
                    name: medicine.displayName,
                    time: schedulePlan.time === "13:00" ? "1:00 PM" : "8:00 AM",
                    period: schedulePlan.period,
                    food: null,
                  },
                ]
              : [],
          ]),
        ),
      },
    });
  });

  await page.goto("/");
  await page.getByRole("searchbox").fill("ibuprofen");
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("link", { name: "Ibuprofen Dye Free" }).click();
  await expect(page.getByRole("heading", { name: "Warnings" })).toBeVisible();
  await expect(
    page.getByText("Ask a doctor. <script>not markup</script>"),
  ).toBeVisible();
  await expect(page.locator(".label-section script")).toHaveCount(0);
  await page.getByRole("button", { name: "Sign in to save" }).click();
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill("strong-password-123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Save to My Medication" }).click();
  await expect(page.getByText("Saved to My Medication")).toBeVisible();
  await page.getByRole("link", { name: "View My Medication" }).click();
  await expect(
    page.getByRole("link", { name: "Ibuprofen Dye Free" }),
  ).toBeVisible();
  await expect(
    page.getByText("Add another medicine to check pairs."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Schedule", exact: true }).click();
  await page.getByRole("button", { name: "Fri", exact: true }).click();
  await page.getByRole("button", { name: "Sat", exact: true }).click();
  await page.getByRole("button", { name: "Sun", exact: true }).click();
  await page.getByRole("button", { name: "afternoon", exact: true }).click();
  await expect(page.getByLabel("Exact time")).toHaveValue("13:00");
  await page.getByRole("button", { name: "Add to pill case" }).click();
  await expect(
    page.getByRole("button", { name: "Edit schedule" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Monday/ }).click();
  await expect(page.locator(".organizer-details")).toContainText(
    "Ibuprofen Dye Free",
  );
  await expect(page.locator(".organizer-details")).toContainText(
    "afternoon · 1:00 PM",
  );
  await page.getByRole("button", { name: /Saturday/ }).click();
  await expect(page.locator(".organizer-details")).toContainText(
    "Ibuprofen Dye Free",
  );
  await page.getByRole("button", { name: /Sunday/ }).click();
  await expect(page.locator(".organizer-details")).toContainText(
    "Ibuprofen Dye Free",
  );
  await page.reload();
  await expect(
    page.getByRole("link", { name: "Ibuprofen Dye Free" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Edit schedule" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit schedule" }).click();
  await expect(page.getByLabel("Exact time")).toHaveValue("13:00");
  await page.getByRole("button", { name: "Remove schedule" }).click();
  await expect(
    page.getByRole("button", { name: "Schedule", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".organizer-details")).not.toContainText(
    "Ibuprofen Dye Free",
  );
  await page.getByRole("button", { name: "Remove" }).click();
  await page.getByRole("button", { name: "Confirm remove" }).click();
  await expect(
    page.getByRole("heading", { name: "No saved medicines yet." }),
  ).toBeVisible();
});

test("shows provider errors without losing the search form", async ({
  page,
}) => {
  await page.route("**/api/medications/?**", (route) =>
    route.fulfill({
      status: 503,
      json: {
        error: {
          code: "PROVIDER_UNAVAILABLE",
          message: "Drug information is temporarily unavailable.",
        },
      },
    }),
  );
  await page.goto("/search?q=ibuprofen");
  await expect(page.getByRole("alert")).toHaveText(
    "Drug information is temporarily unavailable.",
  );
  await expect(
    page.getByRole("searchbox", { name: "Medication name" }),
  ).toBeVisible();
});

test("My Medication paginates and refreshes its label check after removal", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const medicines = [
    medicine,
    { ...medicine, externalId: "second-label", displayName: "Aspirin" },
    { ...medicine, externalId: "third-label", displayName: "Third medicine" },
  ].map((item, i) => ({
    ...item,
    savedId: i + 1,
    savedAt: "2026-10-19",
    labelEffectiveDate: null,
    isStale: false,
  }));
  let removed = false;
  await page.route("**/api/auth/**", (route) =>
    route.fulfill({
      json: route.request().url().includes("csrf/")
        ? { csrfToken: "token" }
        : { user: { id: 1, email: "member@example.com" } },
    }),
  );
  await page.route("**/api/saved-medications/**", (route) => {
    if (route.request().method() === "DELETE") {
      removed = true;
      return route.fulfill({ status: 204 });
    }
    const pageNumber = Number(
      new URL(route.request().url()).searchParams.get("page"),
    );
    return route.fulfill({
      json: {
        data:
          pageNumber === 1
            ? medicines
                .slice(0, 2)
                .filter((item) => !removed || item.savedId !== 1)
            : medicines.slice(2),
        pagination: {
          page: pageNumber,
          pageSize: 2,
          hasNextPage: pageNumber === 1,
        },
      },
    });
  });
  await page.route("**/api/saved-medications/interactions/", (route) =>
    route.fulfill({
      json: {
        status: "clear",
        pairsChecked: removed ? 1 : 3,
        totalPairs: removed ? 1 : 3,
        matches: [],
        reason: null,
      },
    }),
  );
  let interactionRequests = 0;
  await page.route("**/api/medications/interactions/check/", (route) => {
    interactionRequests += 1;
    return route.abort();
  });
  await page.goto("/my-medication");
  await expect(
    page.getByRole("link", { name: "Ibuprofen Dye Free" }),
  ).toBeVisible();
  await expect(
    page.getByText("No interaction text found in 3 checked pairs."),
  ).toBeVisible();
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Check labels" })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Third medicine" }),
  ).toBeVisible();
  expect(interactionRequests).toBe(0);
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await page
    .getByRole("button", { name: "Remove", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Confirm remove" }).click();
  await expect(
    page.getByText("No interaction text found in 1 checked pair."),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Ibuprofen Dye Free" }),
  ).toHaveCount(0);
  expect(interactionRequests).toBe(0);
  expect(errors).toEqual([]);
});

test("saved interaction card shows matched sources and partial checks", async ({
  page,
}) => {
  await page.route("**/api/auth/**", (route) =>
    route.fulfill({ json: { user: { id: 1, email: "member@example.com" } } }),
  );
  await page.route("**/api/saved-medications/?**", (route) =>
    route.fulfill({
      json: {
        data: [
          {
            ...medicine,
            savedId: 1,
            savedAt: "2026-10-19",
            labelEffectiveDate: null,
            isStale: false,
          },
        ],
        pagination,
      },
    }),
  );
  await page.route("**/api/saved-medications/interactions/", (route) =>
    route.fulfill({
      json: {
        status: "match",
        pairsChecked: 1,
        totalPairs: 2,
        reason: "missing_label",
        matches: [
          {
            names: ["Ibuprofen", "Aspirin"],
            findings: [
              {
                sourceMedication: "Ibuprofen",
                targetMedication: "Aspirin",
                matchedTerm: "aspirin",
                text: "Ask a pharmacist about aspirin.",
                sourceUrl: "https://api.fda.gov/drug/label.json",
                labelEffectiveDate: "2026-10-19",
                datasetUpdatedAt: null,
              },
            ],
          },
        ],
      },
    }),
  );
  await page.goto("/my-medication");
  await expect(
    page.getByText("Potential interaction information found in 1 pair."),
  ).toBeVisible();
  await expect(
    page.getByText("Some pairs could not be checked."),
  ).toBeVisible();
  await page.getByText("Review matches").click();
  await expect(page.getByRole("link", { name: /View source/ })).toBeVisible();
  await expect(page.getByText("Ask a pharmacist about aspirin.")).toBeVisible();
});

test("typing in search and account inputs keeps the page rendered", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/auth/me/", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  await page.goto("/");
  await page
    .getByRole("searchbox")
    .pressSequentially("ibuprofen aspirin", { delay: 30 });
  await expect(
    page.getByRole("heading", { name: "MedCheck", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page
    .getByLabel("Email", { exact: true })
    .pressSequentially("member@example.com", { delay: 30 });
  await page
    .getByLabel("Password", { exact: true })
    .pressSequentially("test-password", { delay: 30 });
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue(
    "member@example.com",
  );
  expect(errors).toEqual([]);
});

test("unexpected rendering failures show recovery instead of a white page", async ({
  page,
}) => {
  await page.route("**/api/auth/me/", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  let broken = true;
  await page.route("**/api/medications/?**", (route) =>
    route.fulfill({ json: { data: broken ? [null] : [medicine], pagination } }),
  );
  await page.goto("/search?q=ibuprofen");
  await expect(
    page.getByRole("heading", { name: "Something went wrong" }),
  ).toBeVisible();
  broken = false;
  await page.getByRole("button", { name: "Reload page" }).click();
  await expect(
    page.getByRole("link", { name: medicine.displayName }),
  ).toBeVisible();
});
