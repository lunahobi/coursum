import { expect, test } from "@playwright/test";
import { mockApi, seedAuthenticatedSession } from "./helpers";

test("authenticated user can open all main UI pages", async ({ page }) => {
  await seedAuthenticatedSession(page);
  await mockApi(page);

  const pages: Array<{ path: string; heading: RegExp }> = [
    { path: "/", heading: /dashboard|дашборд/i },
    { path: "/tenants", heading: /tenant|организац/i },
    { path: "/users", heading: /users|пользовател/i },
    { path: "/courses", heading: /courses|курсы/i },
    { path: "/lessons", heading: /lessons|уроки/i },
    { path: "/tests", heading: /tests|тест/i },
    { path: "/assignments", heading: /assignments|практик/i },
    { path: "/homework-reviews", heading: /homework|проверк/i },
    { path: "/analytics", heading: /analytics|аналитик/i },
    { path: "/settings", heading: /settings|настройк/i },
  ];

  for (const entry of pages) {
    await page.goto(entry.path);
    await expect(page.getByRole("heading", { level: 1, name: entry.heading })).toBeVisible();
  }
});
