import { expect, test } from "@playwright/test";

test("centers MedCheck above the search bar", async ({ page }) => {
  await page.goto("/");

  const heading = page.getByRole("heading", { name: "MedCheck" });
  const searchbox = page.getByRole("searchbox", {
    name: "Search medications, symptoms, or health topics",
  });
  const searchForm = page.getByRole("search");

  await expect(heading).toBeVisible();
  await expect(searchbox).toBeVisible();
  await expect(page.getByText("MC", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Open menu" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Account" })).toBeVisible();

  const [headingBox, searchFormBox] = await Promise.all([
    heading.boundingBox(),
    searchForm.boundingBox(),
  ]);

  expect(headingBox).not.toBeNull();
  expect(searchFormBox).not.toBeNull();

  const viewportCenter = (page.viewportSize()?.width ?? 0) / 2;
  expect(
    Math.abs(headingBox!.x + headingBox!.width / 2 - viewportCenter),
  ).toBeLessThan(2);
  expect(
    Math.abs(searchFormBox!.x + searchFormBox!.width / 2 - viewportCenter),
  ).toBeLessThan(2);
});

test("shows the submitted search term", async ({ page }) => {
  await page.goto("/");

  const searchbox = page.getByRole("searchbox");
  await searchbox.fill("ibuprofen");
  await searchbox.press("Enter");

  await expect(
    page.getByRole("status").filter({ hasText: "Searching for “ibuprofen”" }),
  ).toBeVisible();
});

test("does not submit an empty search", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("searchbox").press("Enter");

  await expect(page.getByRole("status")).toHaveText("");
});

test("opens the sliding navigation drawer and account panel", async ({
  page,
}) => {
  await page.goto("/");

  const menuButton = page.getByRole("button", { name: "Open menu" });
  const accountButton = page.getByRole("button", {
    name: "Account",
    exact: true,
  });
  const drawer = page.getByRole("navigation", { name: "Menu" });

  await expect(drawer).toBeHidden();
  await menuButton.click();
  await expect(drawer).toBeVisible();
  await expect(page.getByRole("link", { name: "Home" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Saved Medicines" })).toHaveCount(
    0,
  );
  await expect(page.getByRole("button", { name: "Close menu" })).toBeVisible();
  await expect(menuButton).toHaveAttribute("aria-expanded", "true");

  await page.getByRole("button", { name: "Close menu" }).click({
    position: { x: 400, y: 200 },
  });
  await accountButton.click();
  await expect(page.getByText("Account", { exact: true })).toBeVisible();
  await expect(drawer).toBeHidden();
  await expect(accountButton).toHaveAttribute("aria-expanded", "true");
});

test("closes the navigation menu with Escape and restores focus", async ({
  page,
}) => {
  await page.goto("/");

  const menuButton = page.getByRole("button", { name: "Open menu" });
  await menuButton.click();
  await page.keyboard.press("Escape");

  await expect(page.getByRole("navigation", { name: "Menu" })).toBeHidden();
  await expect(menuButton).toBeFocused();
  await expect(menuButton).toHaveAttribute("aria-expanded", "false");
});

test("closes the navigation drawer from its backdrop", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("button", { name: "Close menu" }).click({
    position: { x: 400, y: 200 },
  });

  await expect(page.getByRole("navigation", { name: "Menu" })).toBeHidden();
});

test("redirects logged-out users away from Saved Medicines", async ({
  page,
}) => {
  await page.goto("/saved-medicines");

  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { name: "MedCheck" })).toBeVisible();
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("link", { name: "Saved Medicines" })).toHaveCount(
    0,
  );
});
