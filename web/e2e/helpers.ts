import type { Page, Route } from "@playwright/test";

const SESSION_STORAGE_KEY = "coursum-web-session";
const LANGUAGE_STORAGE_KEY = "coursum-web-language";

function json(route: Route, payload: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

export async function seedAuthenticatedSession(page: Page) {
  await page.addInitScript(
    ({ sessionKey, languageKey }) => {
      window.localStorage.setItem(
        sessionKey,
        JSON.stringify({
          accessToken: "e2e-token",
          tenantCode: "acme",
          refreshToken: "e2e-refresh",
        }),
      );
      window.localStorage.setItem(languageKey, "en");
    },
    { sessionKey: SESSION_STORAGE_KEY, languageKey: LANGUAGE_STORAGE_KEY },
  );
}

export async function mockApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method().toUpperCase();
    const path = new URL(request.url()).pathname.replace(/\/api\/v1/, "");

    if (method === "POST" && path === "/auth/login") {
      return json(route, {
        access_token: "e2e-token",
        refresh_token: "e2e-refresh",
        token_type: "bearer",
      });
    }
    if (path === "/auth/me") {
      return json(route, {
        id: 1,
        email: "teacher-a@example.com",
        full_name: "Teacher A",
        tenant_role: "org_admin",
      });
    }
    if (path === "/tenants") {
      return json(route, [
        { id: 1, name: "Acme Learning", code: "acme", locale: "en", is_active: true },
        { id: 2, name: "Beta Skills", code: "beta", locale: "en", is_active: true },
      ]);
    }
    if (path === "/tenants/current") {
      return json(route, { id: 1, name: "Acme Learning", code: "acme", locale: "en", is_active: true });
    }
    if (path === "/users") {
      return json(route, [
        { id: 1, email: "teacher-a@example.com", full_name: "Teacher A", role_name: "org_admin", is_active: true },
        { id: 2, email: "learner-a@example.com", full_name: "Learner A", role_name: "learner", is_active: true },
      ]);
    }
    if (path === "/courses") {
      return json(route, [
        { id: 1, title: "Cyber Hygiene", description: "Core security", status: "published", is_published: true },
      ]);
    }
    if (path === "/lessons") {
      return json(route, []);
    }
    if (path === "/tests") {
      return json(route, []);
    }
    if (path === "/groups") {
      return json(route, []);
    }
    if (path.startsWith("/groups/")) {
      return json(route, []);
    }
    if (path.startsWith("/assignments")) {
      return json(route, []);
    }
    if (path.startsWith("/submissions")) {
      return json(route, []);
    }
    if (path === "/analytics/dashboard") {
      return json(route, { users: 12, active_attempts: 5, avg_progress: 67, recommendations: 4, courses: 3, tests: 6, enrollments: 10 });
    }
    if (path === "/analytics/course-progress") {
      return json(route, [{ course_id: 1, course_title: "Cyber Hygiene", avg_progress: 67, learners: 12 }]);
    }
    if (path === "/analytics/problem-topics") {
      return json(route, [{ topic_title: "Password hygiene", recommendations: 3 }]);
    }
    if (path.startsWith("/analytics/timeline")) {
      return json(route, {
        labels: ["01 May", "02 May", "03 May", "04 May"],
        attempts: [1, 2, 3, 4],
        completions: [0, 1, 2, 3],
      });
    }
    if (path.startsWith("/analytics/learners/")) {
      return json(route, {
        results: [{ score_percent: 72, weak_topics: [{ topic_title: "Listening" }] }],
        recommendations: [{ text: "Revise listening", priority: 1, topic_title: "Listening", signal_level: "high" }],
      });
    }
    if (path === "/recommendations/me") {
      return json(route, []);
    }
    if (path === "/media/library") {
      return json(route, []);
    }

    if (method === "DELETE") {
      return json(route, { deleted: true });
    }
    if (method === "POST") {
      return json(route, { id: 1, ok: true });
    }
    if (method === "PATCH" || method === "PUT") {
      return json(route, { id: 1, ok: true });
    }

    return json(route, []);
  });
}
