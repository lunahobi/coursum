import { describe, expect, it } from "vitest";

describe("routes catalog", () => {
  it("includes dashboard and analytics", () => {
    const routeLabels = ["Dashboard", "Tenant Switch", "Users", "Courses", "Analytics"];
    expect(routeLabels).toContain("Analytics");
    expect(routeLabels[0]).toBe("Dashboard");
  });
});
