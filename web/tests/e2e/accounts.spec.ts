import { expect, test } from "@playwright/test";

test("accounts unlock My Medication and survive reload until sign out", async ({
  page,
}) => {
  let signedIn = false;
  const user = {
    id: 1,
    email: "member@example.com",
    username: "member@example.com",
  };
  await page.route("**/api/auth/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("csrf/"))
      return route.fulfill({ json: { csrfToken: "test-token" } });
    if (path.endsWith("me/"))
      return route.fulfill({
        status: signedIn ? 200 : 401,
        json: signedIn ? { user } : {},
      });
    expect(route.request().headers()["x-csrftoken"]).toBe("test-token");
    if (path.endsWith("logout/")) {
      signedIn = false;
      return route.fulfill({ json: { ok: true } });
    }
    const values = route.request().postDataJSON();
    expect(values.email).toBe(user.email);
    if (path.endsWith("register/"))
      expect(values.password_confirmation).toBe(values.password);
    signedIn = true;
    return route.fulfill({
      status: path.endsWith("register/") ? 201 : 200,
      json: { user },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("link", { name: "My Medication" })).toHaveCount(
    0,
  );
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Account", exact: true }).click();
  const signIn = page.getByRole("button", { name: "Sign in", exact: true });
  const create = page.getByRole("button", {
    name: "Create account",
    exact: true,
  });
  expect((await create.boundingBox())!.y).toBeGreaterThan(
    (await signIn.boundingBox())!.y,
  );
  await create.click();
  await page.getByLabel("Email", { exact: true }).fill(user.email);
  await page.getByLabel("Password", { exact: true }).fill("cedar-lantern-482!");
  await page.getByLabel("Confirm password").fill("cedar-lantern-482!");
  await create.click();
  await expect(page.locator("#account-panel")).toHaveCount(0);
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("link", { name: "My Medication" }).click();
  await expect(
    page.getByRole("heading", { name: "My Medication" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "My Medication" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL("/");
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await signIn.click();
  await page.getByLabel("Email", { exact: true }).fill(user.email);
  await page.getByLabel("Password", { exact: true }).fill("cedar-lantern-482!");
  await signIn.click();
  await expect(page.locator("#account-panel")).toHaveCount(0);
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("link", { name: "My Medication" })).toBeVisible();
});

test("failed sign in shows the error and keeps medication private", async ({
  page,
}) => {
  await page.route("**/api/auth/**", (route) => {
    if (route.request().url().endsWith("csrf/"))
      return route.fulfill({ json: { csrfToken: "test-token" } });
    return route.fulfill({
      status: 400,
      json: { errors: { form: "Unable to sign in with those credentials." } },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Unable to sign in with those credentials.",
  );
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("link", { name: "My Medication" })).toHaveCount(
    0,
  );
});

test("reports when Django is unavailable", async ({ page }) => {
  await page.route("**/api/auth/csrf/", (route) => route.abort());
  await page.goto("/");
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password", { exact: true }).fill("a-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "The account service is unavailable. Start Django on port 8000.",
  );
});
