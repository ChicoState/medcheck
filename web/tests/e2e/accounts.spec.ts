import { randomUUID } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

const password = "Test-only-Cedar!4729";

async function register(page: Page, username: string) {
  await page.goto("/register");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL("/");
}

async function signOut(page: Page) {
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect
    .poll(async () => {
      const response = await page.request.get("/api/auth/session/");
      return (await response.json()).user;
    })
    .toBeNull();
}

test("accounts persist, restore their session, and control Saved Medicines access", async ({
  page,
}) => {
  const username = `e2e_${randomUUID()}`;
  await register(page, username);

  const session = await page.request.get("/api/auth/session/");
  expect((await session.json()).user.username).toBe(username);
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("link", { name: "Saved Medicines" }).click();
  await expect(
    page.getByRole("heading", { name: "Saved Medicines" }),
  ).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL("/saved-medicines");
  await expect(
    page.getByRole("heading", { name: "Saved Medicines" }),
  ).toBeVisible();
  await signOut(page);
  await page.goto("/saved-medicines");
  await expect(page).toHaveURL("/");
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("link", { name: "Saved Medicines" })).toHaveCount(
    0,
  );

  await page.goto("/sign-in");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL("/");
  await page.goto("/saved-medicines");
  await expect(
    page.getByRole("heading", { name: "Saved Medicines" }),
  ).toBeVisible();
});

test("duplicate registration reports an error without creating a session", async ({
  page,
}) => {
  const username = `e2e_${randomUUID()}`;
  await register(page, username);
  await signOut(page);
  await page.goto("/register");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(/already|exists|taken/i);
  await expect(page).toHaveURL("/register");
  const session = await page.request.get("/api/auth/session/");
  expect((await session.json()).user).toBeNull();
});

test("incorrect credentials report an error and cannot enter the admin portal", async ({
  page,
}) => {
  const username = `e2e_${randomUUID()}`;
  await register(page, username);
  await signOut(page);
  await page.goto("/sign-in");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Wrong-only-Cedar!4729");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    /invalid|incorrect|unable/i,
  );
  await expect(page).toHaveURL("/sign-in");
  const session = await page.request.get("/api/auth/session/");
  expect((await session.json()).user).toBeNull();

  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL("/");
  await page.goto("http://127.0.0.1:8010/admin/");
  await expect(page).toHaveURL(/\/admin\/login\//);
  await expect(
    page.getByRole("link", { name: "Users", exact: true }),
  ).toHaveCount(0);
});
