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
              },
            ]
          : [],
        pagination,
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
  await page.reload();
  await expect(
    page.getByRole("link", { name: "Ibuprofen Dye Free" }),
  ).toBeVisible();
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
