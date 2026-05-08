import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppTestProviders } from "./App";
import AssignmentsPage from "./pages/AssignmentsPage";

const { apiRequestMock, apiPostMock, apiDeleteMock } = vi.hoisted(() => ({
  apiRequestMock: vi.fn(),
  apiPostMock: vi.fn(),
  apiDeleteMock: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    apiRequest: apiRequestMock,
    apiPost: apiPostMock,
    apiDelete: apiDeleteMock,
  };
});

const session = { accessToken: "token", tenantCode: "acme" };

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/assignments"]}>
      <AppTestProviders language="ru">
        <AssignmentsPage session={session} />
      </AppTestProviders>
    </MemoryRouter>,
  );
}

describe("AssignmentsPage", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
    apiPostMock.mockReset();
    apiDeleteMock.mockReset();
    apiPostMock.mockResolvedValue({});
    apiDeleteMock.mockResolvedValue({});
    vi.spyOn(window, "confirm").mockReturnValue(true);
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [
          {
            id: 1,
            title: "Alpha course",
            description: "alpha",
            is_published: true,
            status: "published",
            image_url: null,
          },
          {
            id: 2,
            title: "Beta archive",
            description: "legacy",
            is_published: false,
            status: "archived",
            image_url: null,
          },
        ];
      }
      if (path === "/users") {
        return [
          { id: 7, email: "learner7@example.com", full_name: "Learner Seven", is_active: true, role_name: "learner" },
          { id: 8, email: "learner8@example.com", full_name: "Learner Eight", is_active: true, role_name: "learner" },
          { id: 9, email: "teacher9@example.com", full_name: "Teacher Nine", is_active: true, role_name: "teacher" },
        ];
      }
      if (path === "/groups") {
        return [{ id: 3, name: "Group A", member_count: 2 }];
      }
      if (path === "/groups/3/members") {
        return [{ id: 21, group_id: 3, user_id: 7, full_name: "Learner Seven", email: "learner7@example.com" }];
      }
      if (path === "/courses/1/assignments") {
        return [
          {
            id: 3,
            user_id: 8,
            group_id: null,
            assigned_by_id: 2,
            created_at: "2026-05-01T10:00:00Z",
            effective_user_ids: [8],
          },
        ];
      }
      if (path === "/courses/2/assignments") {
        return [];
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });
  });

  it("renders courses list from useRemote data", async () => {
    renderPage();
    expect(await screen.findByRole("button", { name: /Alpha course/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Beta archive/i })).toBeInTheDocument();
  });

  it("filters courses by search query", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("button", { name: /Alpha course/i });
    await user.type(screen.getByPlaceholderText("Поиск по названию или описанию"), "beta");
    await waitFor(() => expect(screen.queryByRole("button", { name: /Alpha course/i })).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Beta archive/i })).toBeInTheDocument();
  });

  it("switches right panel when course tile clicked", async () => {
    const user = userEvent.setup();
    renderPage();
    const courseTile = await screen.findByRole("button", { name: /Alpha course/i });
    await user.click(courseTile);
    expect(await screen.findByRole("heading", { name: "Alpha course" })).toBeInTheDocument();
  });

  it("switches Assigned/Assign tabs", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Alpha course/i }));
    expect(await screen.findByRole("button", { name: "Отозвать" })).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Назначить" }));
    expect(await screen.findByLabelText("Learner Seven")).toBeInTheDocument();
  });

  it("calls assign endpoint for single learner action", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Alpha course/i }));
    await user.click(screen.getByRole("tab", { name: "Назначить" }));
    const row = await screen.findByText("Learner Seven");
    const assignButton = within(row.closest(".assignment-row") as HTMLElement).getByRole("button", {
      name: "Назначить",
    });
    await user.click(assignButton);

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith("/courses/1/assign", session, { user_id: 7 });
    });
  });

  it("submits bulk assign as multiple POST calls", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Alpha course/i }));
    await user.click(screen.getByRole("tab", { name: "Назначить" }));

    const learnerSeven = await screen.findByLabelText("Learner Seven");
    const teacherNine = await screen.findByLabelText("Teacher Nine");
    await user.click(learnerSeven);
    await user.click(teacherNine);
    await user.click(screen.getByRole("button", { name: "Назначить выбранных (2)" }));

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith("/courses/1/assign", session, { user_id: 7 });
      expect(apiPostMock).toHaveBeenCalledWith("/courses/1/assign", session, { user_id: 9 });
    });
  });

  it("revokes assignment through delete endpoint after confirmation", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Alpha course/i }));
    await user.click(await screen.findByRole("button", { name: "Отозвать" }));

    await waitFor(() => {
      expect(apiDeleteMock).toHaveBeenCalledWith("/courses/1/assignments/3", session);
    });
  });

  it("creates a group from group mode", async () => {
    const user = userEvent.setup();
    apiPostMock.mockImplementation(async (path: string) => {
      if (path === "/groups") {
        return { id: 11, name: "New Cohort", member_count: 0 };
      }
      return {};
    });
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Alpha course/i }));
    await user.click(screen.getByRole("tab", { name: "Назначить" }));
    await user.click(screen.getByRole("button", { name: "По группе" }));
    await user.type(screen.getByPlaceholderText("Название новой группы"), "New Cohort");
    await user.click(screen.getByRole("button", { name: "Создать группу" }));

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith("/groups", session, { name: "New Cohort" });
    });
  });

  it("adds and removes group member in group mode", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /Alpha course/i }));
    await user.click(screen.getByRole("tab", { name: "Назначить" }));
    await user.click(screen.getByRole("button", { name: "По группе" }));
    await user.selectOptions(screen.getByLabelText("Выберите группу"), "3");
    await screen.findByText("Участники группы");
    const comboBoxes = screen.getAllByRole("combobox");
    await user.selectOptions(comboBoxes[1], "8");
    await user.click(screen.getByRole("button", { name: "Добавить в группу" }));
    await user.click(screen.getByRole("button", { name: "Убрать" }));

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledWith("/groups/3/members", session, { user_id: 8 });
      expect(apiDeleteMock).toHaveBeenCalledWith("/groups/3/members/7", session);
    });
  });
});
