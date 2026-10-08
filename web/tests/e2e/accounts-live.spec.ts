import { expect, test } from "@playwright/test";

test("real Django account creation, session restoration, logout and login", async ({
  page,
}) => {
  test.skip(
    process.env.MEDCHECK_LIVE_AUTH !== "1",
    "Requires Django running on port 8000 with an isolated test database.",
  );
  const email = `browser-${Date.now()}@example.com`;
  const password = "cedar-lantern-482!";
  await page.goto("/");
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.locator("#account-panel")).toHaveCount(0);
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("link", { name: "My Medication" }).click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "My Medication" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL("/");
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator("#account-panel")).toHaveCount(0);
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("link", { name: "My Medication" })).toBeVisible();
});
