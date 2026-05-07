import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppTestProviders, HomeworkReviewsPage } from "./App";

const { apiRequestMock, apiPostMock } = vi.hoisted(() => ({
  apiRequestMock: vi.fn(),
  apiPostMock: vi.fn()
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    apiRequest: apiRequestMock,
    apiPost: apiPostMock
  };
});

const session = { accessToken: "token", tenantCode: "acme" };

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/homework-reviews"]}>
      <AppTestProviders language="ru">
        <HomeworkReviewsPage session={session} />
      </AppTestProviders>
    </MemoryRouter>
  );
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location-probe">{`${location.pathname}${location.search}`}</div>;
}

function renderPageWithLocationProbe() {
  return render(
    <MemoryRouter initialEntries={["/homework-reviews"]}>
      <AppTestProviders language="ru">
        <HomeworkReviewsPage session={session} />
        <LocationProbe />
      </AppTestProviders>
    </MemoryRouter>
  );
}

describe("HomeworkReviewsPage", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
    apiPostMock.mockReset();
    apiPostMock.mockResolvedValue({});
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/assignments") {
        return [
          {
            id: 1,
            course_id: 1,
            lesson_id: 1,
            page_id: "practice-page-42",
            title: "Деловые коммуникации",
            description: "Практическое задание",
            is_active: true,
            created_at: "2026-05-01T12:00:00Z"
          }
        ];
      }
      if (path === "/lessons?course_id=1") {
        return [
          {
            id: 1,
            course_id: 1,
            title: "Урок 1",
            summary: "",
            content_pages: [
              { page_id: "theory-page-1", page_title: "Теория", is_practice: false },
              { page_id: "practice-page-42", page_title: "Практика по заданию", is_practice: false },
              { page_id: "practice-page-1", page_title: "Практика", is_practice: true }
            ]
          }
        ];
      }
      if (path === "/users") {
        return [{ id: 4, email: "ivan@example.com", full_name: "Иван Иванов", is_active: true }];
      }
      if (path === "/assignments/1/submissions") {
        return [
          {
            id: 42,
            assignment_id: 1,
            student_user_id: 4,
            status: "submitted",
            text_answer: "Ответ ученика",
            link_answer: "https://example.com/work",
            submitted_at: "2026-05-01T10:00:00Z",
            updated_at: "2026-05-01T10:05:00Z",
            files: [{ id: 7, file_url: "/media/acme/file-1.txt", file_name: "Файл решения.txt", created_at: "2026-05-01T10:05:00Z" }],
            latest_review: {
              id: 12,
              reviewer_user_id: 2,
              status: "in_review",
              comment: "Проверяю",
              grade: null,
              created_at: "2026-05-01T10:10:00Z"
            }
          }
        ];
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });
  });

  it("shows learner full name instead of raw user id", async () => {
    renderPage();
    expect(await screen.findByText("Иван Иванов")).toBeInTheDocument();
    expect(screen.queryByText(/user 4/i)).not.toBeInTheDocument();
  });

  it("renders submission content: text, link, and file", async () => {
    renderPage();
    expect(await screen.findByText("Ответ ученика")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://example.com/work" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Файл решения.txt" })).toBeInTheDocument();
  });

  it("sends status, comment and grade in review payload", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Ответ ученика");
    await user.selectOptions(screen.getByLabelText("Статус проверки"), "approved");
    await user.clear(screen.getByLabelText("Оценка (0-100)"));
    await user.type(screen.getByLabelText("Оценка (0-100)"), "85");
    await user.clear(screen.getByLabelText("Комментарий куратора"));
    await user.type(screen.getByLabelText("Комментарий куратора"), "Отлично");
    await user.click(screen.getByRole("button", { name: "Сохранить проверку" }));

    await waitFor(() =>
      expect(apiPostMock).toHaveBeenCalledWith("/submissions/42/review", session, {
        status: "approved",
        comment: "Отлично",
        grade: 85
      })
    );
  });

  it("sends null grade when grade field is empty", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Ответ ученика");

    await user.clear(screen.getByLabelText("Оценка (0-100)"));
    await user.clear(screen.getByLabelText("Комментарий куратора"));
    await user.type(screen.getByLabelText("Комментарий куратора"), "Без оценки");
    await user.click(screen.getByRole("button", { name: "Сохранить проверку" }));

    await waitFor(() =>
      expect(apiPostMock).toHaveBeenCalledWith("/submissions/42/review", session, {
        status: "in_review",
        comment: "Без оценки",
        grade: null
      })
    );
  });

  it("opens linked practice page directly", async () => {
    const user = userEvent.setup();
    renderPageWithLocationProbe();
    await screen.findByRole("button", { name: "Открыть задание" });

    await user.click(screen.getByRole("button", { name: "Открыть задание" }));

    await waitFor(() => {
      const location = screen.getByTestId("location-probe").textContent || "";
      expect(location.startsWith("/lessons?")).toBe(true);
      const search = new URLSearchParams(location.slice(location.indexOf("?") + 1));
      expect(search.get("courseId")).toBe("1");
      expect(search.get("lessonId")).toBe("1");
      expect(search.get("pageId")).toBe("practice-page-1");
      expect(search.get("assignmentId")).toBe("1");
      expect(search.get("assignmentTitle")).toBe("Деловые коммуникации");
      expect(search.get("openPractice")).toBe("1");
    });
  });
});
