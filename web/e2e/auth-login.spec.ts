import { expect, test } from "@playwright/test";
import { mockApi } from "./helpers";

test("login page renders base fields", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /coursum/i })).toBeVisible();
  await expect(page.getByRole("textbox", { name: /email/i })).toBeVisible();
  await expect(page.getByPlaceholder(/password|пароль/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /login|войти/i })).toBeVisible();
});

test("user can submit login form and enter dashboard", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");

  await page.getByPlaceholder(/email/i).fill("teacher-a@example.com");
  await page.getByPlaceholder(/password|пароль/i).fill("Password123!");
  await page.getByPlaceholder(/tenant|организа/i).fill("acme");
  await page.getByRole("button", { name: /login|войти/i }).click();

  await expect(page.getByRole("heading", { name: /dashboard|дашборд/i })).toBeVisible();
});
