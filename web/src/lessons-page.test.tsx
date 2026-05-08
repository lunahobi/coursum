import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppTestProviders, LessonsPage, MediaAttachmentCard, MediaPickerDialog } from "./App";

const { apiPatchMock, apiRequestMock, apiUploadMock } = vi.hoisted(() => ({
  apiPatchMock: vi.fn(),
  apiRequestMock: vi.fn(),
  apiUploadMock: vi.fn()
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    apiRequest: apiRequestMock,
    apiUpload: apiUploadMock,
    apiPost: vi.fn(),
    apiPatch: apiPatchMock
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
    path: "/media/customer-service-image.png",
    label: "Customer service image",
    kind: "image" as const,
    size_bytes: 1024,
    filename: "customer-service-image.png",
    mime_type: "image/png"
  },
  {
    path: "/media/customer-service-video.mp4",
    label: "Customer service video",
    kind: "video" as const,
    size_bytes: 2048,
    filename: "customer-service-video.mp4",
    mime_type: "video/mp4"
  }
];

const emptySections: Array<{ id: number; course_id: number; title: string; sort_order: number; is_visible: boolean }> = [];
const emptyRecommendations: Array<{ id: number; title: string; text: string; course_id: number; lesson_id: number | null; is_active: boolean; sort_order: number; tenant_id: number }> = [];

function makeLesson(id: number) {
  return {
    id,
    course_id: 1,
    title: `Lesson ${id}`,
    summary: `Summary for lesson ${id}.`,
    content: `Legacy lesson content ${id}.`,
    content_pages: [
      {
        page_id: `lesson-${id}-page-1`,
        chapter_title: "Context",
        page_title: `Lesson ${id} page`,
        blocks: [{ type: "html", html: `<p>Lesson ${id} body.</p>` }]
      }
    ],
    duration_minutes: 8 + id,
    image_url: null,
    video_url: null,
    sort_order: id
  };
}

const lessons = Array.from({ length: 8 }, (_, index) => makeLesson(index + 1));

const secondCourseLessons = [
  {
    ...makeLesson(1),
    id: 21,
    course_id: 2,
    title: "Leadership kickoff",
    summary: "Start the manager onboarding path.",
    sort_order: 1,
    content_pages: [
      {
        page_id: "leadership-1-page-1",
        chapter_title: "Leadership",
        page_title: "Leadership kickoff",
        blocks: [{ type: "html", html: "<p>Leadership lesson body.</p>" }]
      }
    ]
  }
];

function renderLessonsPage(initialEntries = ["/lessons"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AppTestProviders language="en">
        <LessonsPage session={session} />
      </AppTestProviders>
    </MemoryRouter>
  );
}

function getActivePagePanel() {
  return screen.getByText("Active page").closest("section") as HTMLElement;
}

function MediaHarness({ kind }: { kind: "image" | "video" }) {
  const [url, setUrl] = useState("");
  const [open, setOpen] = useState(false);

  return (
    <AppTestProviders language="en">
      <div>
        <MediaAttachmentCard scope="page" kind={kind} url={url} onAttach={() => setOpen(true)} onRemove={() => setUrl("")} />
        <MediaPickerDialog
          open={open}
          kind={kind}
          assets={mediaAssets}
          onClose={() => setOpen(false)}
          onSelect={(asset) => {
            setUrl(asset.path);
            setOpen(false);
          }}
          onUpload={async (file, nextKind, onProgress) => {
            const uploaded = (await apiUploadMock(file, nextKind, onProgress)) as (typeof mediaAssets)[number];
            return uploaded;
          }}
        />
      </div>
    </AppTestProviders>
  );
}

describe("LessonsPage", () => {
  beforeEach(() => {
    apiPatchMock.mockReset();
    apiRequestMock.mockReset();
    apiUploadMock.mockReset();
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [course, secondCourse];
      }
      if (path === "/media/library") {
        return mediaAssets;
      }
      if (path === "/lessons?course_id=1") {
        return lessons;
      }
      if (path === "/lessons?course_id=2") {
        return secondCourseLessons;
      }
      if (path === "/courses/1/sections" || path === "/courses/2/sections") {
        return emptySections;
      }
      if (path === "/recommendations/editor?course_id=1" || path === "/recommendations/editor?course_id=2") {
        return emptyRecommendations;
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });
  });

  it("keeps the active lesson page selected after saving", async () => {
    const user = userEvent.setup();
    const lessonWithTwoPages = {
      ...makeLesson(3),
      content_pages: [
        {
          page_id: "stable-page-1",
          chapter_title: "Context",
          page_title: "First page",
          blocks: [{ type: "html", html: "<p>First body.</p>" }]
        },
        {
          page_id: "stable-page-2",
          chapter_title: "Practice",
          page_title: "Second page",
          blocks: [{ type: "html", html: "<p>Second body.</p>" }]
        }
      ]
    };
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return [course];
      }
      if (path === "/media/library") {
        return mediaAssets;
      }
      if (path === "/lessons?course_id=1") {
        return [lessonWithTwoPages];
      }
      if (path === "/courses/1/sections") {
        return emptySections;
      }
      if (path === "/recommendations/editor?course_id=1") {
        return emptyRecommendations;
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });
    apiPatchMock.mockImplementation(async (_path: string, _session: typeof session, payload: { content_pages: typeof lessonWithTwoPages.content_pages }) => ({
      ...lessonWithTwoPages,
      content_pages: payload.content_pages.map((page, index) => ({
        ...page,
        page_id: `server-page-${index + 1}`
      }))
    }));

    renderLessonsPage();

    await user.click(await screen.findByRole("button", { name: /2\. Second page/i }));
    expect(screen.getByRole("heading", { name: "Second page" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save lesson" }));

    await waitFor(() => expect(apiPatchMock).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("heading", { name: "Second page" })).toBeInTheDocument();
    expect(screen.getByText("2 / 2")).toBeInTheDocument();
  });

  it("respects courseId from the url when opening the lesson editor", async () => {
    renderLessonsPage(["/lessons?courseId=2"]);

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Course" })).toHaveValue("2"));
    expect(screen.getByRole("link", { name: "Edit course" })).toHaveAttribute("href", "/courses?courseId=2");
    expect(await screen.findByRole("heading", { name: "Leadership kickoff" })).toBeInTheDocument();
  });

  it("renders the complete lesson list and keeps the last lesson accessible", async () => {
    const { container } = renderLessonsPage();

    const sidebarList = await screen.findByTestId("lessons-sidebar-list");
    await waitFor(() => expect(sidebarList.querySelectorAll(".lessons-lesson-card")).toHaveLength(8));
    expect(sidebarList).toBeInTheDocument();
    expect(within(sidebarList).getAllByText("Lesson 8")[0]).toBeInTheDocument();
    expect(container.querySelectorAll(".lessons-sidebar-list")).toHaveLength(1);
  });

  it("opens the image modal from the lessons page", async () => {
    const user = userEvent.setup();
    renderLessonsPage();

    await waitFor(() => expect(screen.getAllByRole("button", { name: "Attach image" }).length).toBeGreaterThan(0));
    await user.click(within(getActivePagePanel()).getByRole("button", { name: "Attach image" }));

    expect(screen.getByRole("dialog", { name: "Image picker" })).toBeInTheDocument();
  });

  it("uploads an image into the active page HTML", async () => {
    apiUploadMock.mockResolvedValue({
      path: "/media/uploaded-inline-image.png",
      label: "Uploaded inline image",
      kind: "image" as const,
      size_bytes: 4096,
      filename: "uploaded-inline-image.png",
      mime_type: "image/png"
    });
    const user = userEvent.setup();
    renderLessonsPage();

    await waitFor(() => expect(within(getActivePagePanel()).getAllByRole("button", { name: "Insert image" }).length).toBeGreaterThan(0));
    await user.click(within(getActivePagePanel()).getAllByRole("button", { name: "Insert image" })[0]);

    const dialog = screen.getByRole("dialog", { name: "Image picker" });
    const fileInput = dialog.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    const file = new File(["image-binary"], "uploaded-inline-image.png", { type: "image/png" });
    await user.upload(fileInput!, file);
    await user.click(screen.getByRole("button", { name: "Upload and select" }));

    await waitFor(() => expect(apiUploadMock).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect((within(getActivePagePanel()).getByLabelText("HTML source") as HTMLTextAreaElement).value).toContain(
        '<img src="/media/uploaded-inline-image.png" alt="Uploaded inline image" />'
      )
    );
  });

  it("uploads a local image and shows the preview in the media field", async () => {
    apiUploadMock.mockResolvedValue({
      path: "/media/uploaded-image.png",
      label: "Uploaded image",
      kind: "image" as const,
      size_bytes: 4096,
      filename: "uploaded-image.png",
      mime_type: "image/png"
    });
    const user = userEvent.setup();
    render(<MediaHarness kind="image" />);

    await user.click(screen.getByRole("button", { name: "Attach image" }));

    const dialog = screen.getByRole("dialog", { name: "Image picker" });
    expect(dialog).toBeInTheDocument();
    const fileInput = dialog.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    const file = new File(["image-binary"], "uploaded-image.png", { type: "image/png" });
    await user.upload(fileInput!, file);
    await user.click(screen.getByRole("button", { name: "Upload and select" }));

    await waitFor(() => expect(apiUploadMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(within(screen.getByTestId("media-attachment-page-image")).getByText("/media/uploaded-image.png")).toBeInTheDocument());
    const card = screen.getByTestId("media-attachment-page-image");
    const image = card.querySelector("img");
    expect(image).not.toBeNull();
    expect(image).toHaveAttribute("src", expect.stringContaining("/media/uploaded-image.png"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the video modal from the lessons page", async () => {
    const user = userEvent.setup();
    renderLessonsPage();

    await waitFor(() => expect(screen.getAllByRole("button", { name: "Attach video" }).length).toBeGreaterThan(0));
    await user.click(within(getActivePagePanel()).getByRole("button", { name: "Attach video" }));

    expect(screen.getByRole("dialog", { name: "Video picker" })).toBeInTheDocument();
  });

  it("inserts a video from the media library into the active page HTML", async () => {
    const user = userEvent.setup();
    renderLessonsPage();

    await screen.findByRole("heading", { name: "Lesson 1 page" });
    const activePanel = getActivePagePanel();
    const htmlSource = within(activePanel).getByLabelText("HTML source") as HTMLTextAreaElement;
    htmlSource.focus();
    htmlSource.setSelectionRange(3, 3);
    fireEvent.select(htmlSource);

    await waitFor(() => expect(within(activePanel).getAllByRole("button", { name: "Insert video" }).length).toBeGreaterThan(0));
    await user.click(within(activePanel).getAllByRole("button", { name: "Insert video" })[0]);
    await user.click(screen.getByRole("button", { name: "Library" }));
    await user.click(screen.getByRole("button", { name: "Select" }));

    await waitFor(() =>
      expect((within(activePanel).getByLabelText("HTML source") as HTMLTextAreaElement).value).toContain(
        '<p><video controls preload="metadata" playsinline src="/media/customer-service-video.mp4"></video>Lesson 1 body.</p>'
      )
    );
  });

  it("uploads a local video and shows the preview in the media field", async () => {
    apiUploadMock.mockResolvedValue({
      path: "/media/uploaded-video.mp4",
      label: "Uploaded video",
      kind: "video" as const,
      size_bytes: 8192,
      filename: "uploaded-video.mp4",
      mime_type: "video/mp4"
    });
    const user = userEvent.setup();
    render(<MediaHarness kind="video" />);

    await user.click(screen.getByRole("button", { name: "Attach video" }));

    const dialog = screen.getByRole("dialog", { name: "Video picker" });
    expect(dialog).toBeInTheDocument();
    const fileInput = dialog.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    const file = new File(["video-binary"], "uploaded-video.mp4", { type: "video/mp4" });
    await user.upload(fileInput!, file);
    await user.click(screen.getByRole("button", { name: "Upload and select" }));

    await waitFor(() => expect(apiUploadMock).toHaveBeenCalledTimes(1));

    await waitFor(() =>
      expect(within(screen.getByTestId("media-attachment-page-video")).getByText("/media/uploaded-video.mp4")).toBeInTheDocument()
    );
    const card = screen.getByTestId("media-attachment-page-video");
    expect(card.querySelector("video")).not.toBeNull();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("can select an existing image from the media library", async () => {
    const user = userEvent.setup();
    render(<MediaHarness kind="image" />);

    await user.click(screen.getByRole("button", { name: "Attach image" }));
    await user.click(screen.getByRole("button", { name: "Library" }));
    await user.click(screen.getByRole("button", { name: "Select" }));

    const card = screen.getByTestId("media-attachment-page-image");
    expect(within(card).getByText("/media/customer-service-image.png")).toBeInTheDocument();
  });

  it("shows upload progress while a video is uploading", async () => {
    let finishUpload: (() => void) | undefined;
    apiUploadMock.mockImplementation(
      (_file: File, _kind: "image" | "video", onProgress?: (progress: number) => void) =>
        new Promise((resolve) => {
          onProgress?.(37);
          finishUpload = () =>
            resolve({
              path: "/media/uploaded-video.mp4",
              label: "Uploaded video",
              kind: "video" as const,
              size_bytes: 8192,
              filename: "uploaded-video.mp4",
              mime_type: "video/mp4"
            });
        })
    );
    const user = userEvent.setup();
    render(<MediaHarness kind="video" />);

    await user.click(screen.getByRole("button", { name: "Attach video" }));

    const dialog = screen.getByRole("dialog", { name: "Video picker" });
    const fileInput = dialog.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    const file = new File(["video-binary"], "uploaded-video.mp4", { type: "video/mp4" });
    await user.upload(fileInput!, file);
    await user.click(screen.getByRole("button", { name: "Upload and select" }));

    await waitFor(() => expect(screen.getByRole("progressbar", { name: "Upload progress" })).toHaveAttribute("aria-valuenow", "37"));

    finishUpload?.();

    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Video picker" })).not.toBeInTheDocument());
  });

  it("switches to server processing state after the file reaches the backend", async () => {
    let finishUpload: (() => void) | undefined;
    apiUploadMock.mockImplementation(
      (_file: File, _kind: "image" | "video", onProgress?: (progress: number) => void) =>
        new Promise((resolve) => {
          onProgress?.(100);
          finishUpload = () =>
            resolve({
              path: "/media/uploaded-video.mp4",
              label: "Uploaded video",
              kind: "video" as const,
              size_bytes: 8192,
              filename: "uploaded-video.mp4",
              mime_type: "video/mp4"
            });
        })
    );
    const user = userEvent.setup();
    render(<MediaHarness kind="video" />);

    await user.click(screen.getByRole("button", { name: "Attach video" }));

    const dialog = screen.getByRole("dialog", { name: "Video picker" });
    const fileInput = dialog.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    const file = new File(["video-binary"], "uploaded-video.mp4", { type: "video/mp4" });
    await user.upload(fileInput!, file);
    await user.click(screen.getByRole("button", { name: "Upload and select" }));

    await waitFor(() => expect(screen.getByRole("progressbar", { name: "Upload progress" })).toHaveAttribute("aria-valuenow", "99"));
    expect(screen.getByText("Server is processing the file...")).toBeInTheDocument();
    expect(
      screen.getByText("The file is already uploaded. Waiting for the server to finish saving it and preparing the video.")
    ).toBeInTheDocument();

    finishUpload?.();

    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Video picker" })).not.toBeInTheDocument());
  });

  it("keeps advanced sections collapsed by default and supports keyboard close in the modal", async () => {
    const user = userEvent.setup();
    const { container } = renderLessonsPage();

    await waitFor(() => expect(screen.getAllByRole("button", { name: "Attach video" }).length).toBeGreaterThan(0));
    const advancedPanels = Array.from(container.querySelectorAll("details.advanced-panel")) as HTMLDetailsElement[];
    expect(advancedPanels.length).toBeGreaterThanOrEqual(1);
    expect(advancedPanels.every((panel) => panel.open === false)).toBe(true);
    expect(screen.getAllByLabelText("Lesson title")[0]).toBeVisible();
    expect(screen.getAllByLabelText("Chapter title")[0]).toBeVisible();

    await user.click(within(getActivePagePanel()).getByRole("button", { name: "Attach video" }));
    expect(screen.getByRole("dialog", { name: "Video picker" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Close" })).toHaveFocus());

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
