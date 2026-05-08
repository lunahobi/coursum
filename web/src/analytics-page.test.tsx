import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AnalyticsPage, AppTestProviders } from "./App";

const { apiRequestMock } = vi.hoisted(() => ({
  apiRequestMock: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, apiRequest: apiRequestMock };
});

const session = { accessToken: "token", tenantCode: "acme" };

describe("AnalyticsPage", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/users") {
        return [
          { id: 3, full_name: "Alice Learner", email: "alice@example.com", role_name: "learner", is_active: true },
          { id: 9, full_name: "Bob Teacher", email: "bob@example.com", role_name: "teacher", is_active: true },
        ];
      }
      if (path === "/analytics/dashboard") {
        return { users: 10, active_attempts: 4, avg_progress: 66, recommendations: 2, courses: 5 };
      }
      if (path === "/analytics/learners/3") {
        return {
          results: [{ score_percent: 72, weak_topics: [{ topic_title: "Listening", score: 41 }] }],
          recommendations: [{ text: "Revise listening", priority: 5, topic_title: "Listening", signal_level: "high" }],
        };
      }
      if (path === "/analytics/learners/999") {
        return { results: [], recommendations: [] };
      }
      throw new Error(`Unexpected path ${path}`);
    });
  });

  function renderPage() {
    return render(
      <MemoryRouter>
        <AppTestProviders language="en">
          <AnalyticsPage session={session} />
        </AppTestProviders>
      </MemoryRouter>,
    );
  }

  it("filters learners with search", async () => {
    const user = userEvent.setup();
    renderPage();
    const input = await screen.findByPlaceholderText("Search by name or email");
    await user.type(input, "alice");
    expect(screen.getByText("Alice Learner")).toBeInTheDocument();
    expect(screen.queryByText("Bob Teacher")).not.toBeInTheDocument();
  });

  it("switches attempts and recommendations tabs", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Alice Learner/i }));
    expect(await screen.findByText("No.")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Recommendations" }));
    expect(await screen.findByText("Revise listening")).toBeInTheDocument();
  });

  it("shows empty state before learner selection", async () => {
    renderPage();
    expect(await screen.findByText("Pick a learner on the left to view progress")).toBeInTheDocument();
  });
});
