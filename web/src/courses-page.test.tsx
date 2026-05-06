import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppTestProviders, CoursesPage } from "./App";

const { apiDeleteMock, apiRequestMock, apiPostMock, apiPatchMock } = vi.hoisted(() => ({
  apiDeleteMock: vi.fn(),
  apiRequestMock: vi.fn(),
  apiPostMock: vi.fn(),
  apiPatchMock: vi.fn()
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    apiDelete: apiDeleteMock,
    apiRequest: apiRequestMock,
    apiPost: apiPostMock,
    apiPatch: apiPatchMock,
    apiUpload: vi.fn()
  };
});

const session = { accessToken: "token", tenantCode: "acme" };

const course = {
  id: 1,
  title: "Customer service essentials",
  description: "Keep the course builder focused and easy to manage.",
  is_published: true,
  image_url: "/media/customer-service-cover.png"
};

const secondCourse = {
  id: 2,
  title: "Leadership basics",
  description: "Build the confidence to run team rituals well.",
  is_published: true,
  image_url: "/media/leadership-cover.png"
};

const mediaAssets = [
  {
    path: "/media/customer-service-cover.png",
    label: "Customer Service Cover",
    kind: "image",
    size_bytes: 2048,
    filename: "customer-service-cover.png",
    mime_type: "image/png"
  }
];

function makePreview(payloadCourse: typeof course | typeof secondCourse) {
  return {
    course: payloadCourse,
    sections: [],
    lessons: []
  };
}

function renderCoursesPage(initialEntries = ["/courses"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AppTestProviders language="en">
        <CoursesPage session={session} />
      </AppTestProviders>
    </MemoryRouter>
  );
}

describe("CoursesPage", () => {
  beforeEach(() => {
    apiDeleteMock.mockReset();
    apiRequestMock.mockReset();
    apiPostMock.mockReset();
    apiPatchMock.mockReset();
  });

  it("hides course editing controls for learner accounts", async () => {
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [course];
      }
      if (path === "/lessons?course_id=1") {
        return [];
      }
      if (path === "/courses/1/sections") {
        return [];
      }
      if (path === "/courses/1/staff") {
        return [];
      }
      if (path === "/courses/1/preview") {
        return makePreview(course);
      }
      if (path === "/users") {
        return [];
      }
      if (path === "/media/library") {
        return mediaAssets;
      }
      if (path === "/auth/me") {
        return {
          id: 42,
          email: "learner@acme.example.com",
          full_name: "Learner",
          tenant_role: "learner"
        };
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });

    renderCoursesPage();

    expect(await screen.findByText("Course editor unavailable")).toBeInTheDocument();
    expect(
      screen.getByText("This account is a learner. Only teachers, organization admins, and system admins can create or edit courses.")
    ).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "New course" })).toBeDisabled());
    expect(screen.queryByRole("button", { name: "Create course" })).not.toBeInTheDocument();
  });

  it("deletes the selected course from the editor", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    apiDeleteMock.mockResolvedValue({ deleted: true, course_id: 1, deleted_lessons: 0, deleted_tests: 0 });
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [course];
      }
      if (path === "/lessons?course_id=1") {
        return [];
      }
      if (path === "/courses/1/sections") {
        return [];
      }
      if (path === "/courses/1/staff") {
        return [];
      }
      if (path === "/courses/1/preview") {
        return makePreview(course);
      }
      if (path === "/users") {
        return [];
      }
      if (path === "/media/library") {
        return mediaAssets;
      }
      if (path === "/auth/me") {
        return {
          id: 7,
          email: "teacher@acme.example.com",
          full_name: "Teacher",
          tenant_role: "teacher"
        };
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });

    renderCoursesPage();

    await screen.findByRole("button", { name: "Delete course" });
    await user.click(screen.getByRole("button", { name: "Delete course" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(apiDeleteMock).toHaveBeenCalledWith("/courses/1", session);
    await waitFor(() => expect(screen.getByText("Course archived")).toBeInTheDocument());

    confirmSpy.mockRestore();
  });

  it("keeps the new course draft open and submits via create endpoint", async () => {
    const user = userEvent.setup();
    apiPostMock.mockResolvedValue({
      id: 2,
      title: "New course from test",
      description: "Created in test",
      is_published: true,
      image_url: null
    });
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [course];
      }
      if (path === "/lessons?course_id=1") {
        return [];
      }
      if (path === "/courses/1/sections") {
        return [];
      }
      if (path === "/courses/1/staff") {
        return [];
      }
      if (path === "/courses/1/preview") {
        return makePreview(course);
      }
      if (path === "/users") {
        return [];
      }
      if (path === "/media/library") {
        return mediaAssets;
      }
      if (path === "/auth/me") {
        return {
          id: 7,
          email: "teacher@acme.example.com",
          full_name: "Teacher",
          tenant_role: "teacher"
        };
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });

    renderCoursesPage();

    await screen.findByRole("button", { name: "Save course" });
    await user.click(screen.getByRole("button", { name: "New course" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Create course" })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Delete course" })).not.toBeInTheDocument();

    const titleInput = screen.getByLabelText("Course title");
    await user.type(titleInput, "New course from test");
    await user.click(screen.getByRole("button", { name: "Create course" }));

    expect(apiPatchMock).not.toHaveBeenCalled();
    expect(apiPostMock).toHaveBeenCalledWith("/courses", session, {
      title: "New course from test",
      description: "",
      image_url: null,
      status: "draft",
      category: null,
      access_settings: {
        self_enrollment: false,
        language: "en"
      },
      available_from: null,
      available_to: null
    });
    await waitFor(() => expect(screen.getByText("Course created")).toBeInTheDocument());
  });

  it("selects a course cover from the media library before creating a course", async () => {
    const user = userEvent.setup();
    apiPostMock.mockResolvedValue({
      id: 2,
      title: "New course from test",
      description: "Created in test",
      is_published: true,
      image_url: "/media/customer-service-cover.png"
    });
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [course];
      }
      if (path === "/lessons?course_id=1") {
        return [];
      }
      if (path === "/courses/1/sections") {
        return [];
      }
      if (path === "/courses/1/staff") {
        return [];
      }
      if (path === "/courses/1/preview") {
        return makePreview(course);
      }
      if (path === "/users") {
        return [];
      }
      if (path === "/media/library") {
        return mediaAssets;
      }
      if (path === "/auth/me") {
        return {
          id: 7,
          email: "teacher@acme.example.com",
          full_name: "Teacher",
          tenant_role: "teacher"
        };
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });

    renderCoursesPage();

    await screen.findByRole("button", { name: "Save course" });
    await user.click(screen.getByRole("button", { name: "New course" }));
    await user.click(screen.getByRole("button", { name: "Attach image" }));
    await user.click(screen.getByRole("button", { name: "Library" }));
    await user.click(screen.getByRole("button", { name: "Select" }));

    expect(await screen.findByText("/media/customer-service-cover.png")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Course title"), "New course from test");
    await user.click(screen.getByRole("button", { name: "Create course" }));

    expect(apiPostMock).toHaveBeenCalledWith("/courses", session, {
      title: "New course from test",
      description: "",
      image_url: "/media/customer-service-cover.png",
      status: "draft",
      category: null,
      access_settings: {
        self_enrollment: false,
        language: "en"
      },
      available_from: null,
      available_to: null
    });
  });

  it("opens the lesson editor for the currently selected course", async () => {
    const user = userEvent.setup();
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [course, secondCourse];
      }
      if (path === "/lessons?course_id=1") {
        return [];
      }
      if (path === "/lessons?course_id=2") {
        return [];
      }
      if (path === "/courses/1/sections" || path === "/courses/2/sections") {
        return [];
      }
      if (path === "/courses/1/staff" || path === "/courses/2/staff") {
        return [];
      }
      if (path === "/courses/1/preview") {
        return makePreview(course);
      }
      if (path === "/courses/2/preview") {
        return makePreview(secondCourse);
      }
      if (path === "/users") {
        return [];
      }
      if (path === "/media/library") {
        return mediaAssets;
      }
      if (path === "/auth/me") {
        return {
          id: 7,
          email: "teacher@acme.example.com",
          full_name: "Teacher",
          tenant_role: "teacher"
        };
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });

    renderCoursesPage();

    await screen.findByRole("button", { name: "Save course" });
    await user.click(screen.getByRole("button", { name: /Leadership basics/ }));

    expect(screen.getByRole("link", { name: "Open lesson builder" })).toHaveAttribute("href", "/lessons?courseId=2");
  });
});
