import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppTestProviders, DashboardPage } from "./App";

const { apiRequestMock } = vi.hoisted(() => ({
  apiRequestMock: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, apiRequest: apiRequestMock };
});

const session = { accessToken: "token", tenantCode: "acme" };

describe("DashboardPage", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/analytics/dashboard") {
        return { users: 24, active_attempts: 17, avg_progress: 71, recommendations: 9, courses: 4, tests: 8, enrollments: 43 };
      }
      if (path === "/analytics/course-progress") {
        return [
          { course_title: "A course", avg_progress: 45, learners: 32 },
          { course_title: "B course", avg_progress: 82, learners: 10 },
        ];
      }
      if (path === "/analytics/problem-topics") {
        return [{ topic_title: "Topic 1", recommendations: 4 }];
      }
      throw new Error(`Unexpected path ${path}`);
    });
  });

  function renderPage() {
    return render(
      <MemoryRouter>
        <AppTestProviders language="en">
          <DashboardPage session={session} />
        </AppTestProviders>
      </MemoryRouter>,
    );
  }

  it("renders KPI cards from analytics stats", async () => {
    renderPage();
    expect(await screen.findByText("Learners")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("71%")).toBeInTheDocument();
  });

  it("switches between cards and table views", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Course health");
    await user.click(screen.getByRole("button", { name: "Table" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cards" }));
    expect(screen.getByRole("link", { name: /A course/i })).toBeInTheDocument();
  });

  it("changes course ordering when sort changes", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("link", { name: /B course/i });
    const select = screen.getByDisplayValue("By progress ↓");
    await user.selectOptions(select, "progress_asc");
    const cards = screen.getAllByRole("link").filter((node) => node.getAttribute("href")?.startsWith("/courses?focus="));
    expect(within(cards[0]).getByText("A course")).toBeInTheDocument();
  });
});
