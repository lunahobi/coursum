import { expect, test } from "@playwright/test";
import { mockApi, seedAuthenticatedSession } from "./helpers";

test("dashboard shows activity metrics and chart legend", async ({ page }) => {
  await seedAuthenticatedSession(page);
  await mockApi(page);
  await page.goto("/");

  await expect(page.getByText(/Started:/i)).toBeVisible();
  await expect(page.getByText(/Completed:/i)).toBeVisible();
  await expect(page.getByText(/Conversion:/i)).toBeVisible();
  await expect(page.locator(".dashboard-legend span", { hasText: /^Attempts$/i })).toBeVisible();
  await expect(page.locator(".dashboard-legend span", { hasText: /^Completions$/i })).toBeVisible();
});
