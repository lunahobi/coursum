import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppTestProviders, TestsPage } from "./App";

const { apiPatchMock, apiPostMock, apiRequestMock } = vi.hoisted(() => ({
  apiPatchMock: vi.fn(),
  apiPostMock: vi.fn(),
  apiRequestMock: vi.fn()
}));
const scrollIntoViewMock = vi.fn();

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    apiPatch: apiPatchMock,
    apiPost: apiPostMock,
    apiRequest: apiRequestMock,
    apiDelete: vi.fn(),
    apiUpload: vi.fn()
  };
});

const session = { accessToken: "token", tenantCode: "acme" };

const courses = [
  {
    id: 1,
    title: "Customer service essentials",
    description: "Keep conversations clear, calm, and useful.",
    is_published: true,
    image_url: null
  }
];

const tests = [
  {
    id: 7,
    title: "Customer service baseline",
    course_id: 1,
    baseline_difficulty: 3,
    question_limit: 8,
    question_count: 3
  }
];

const topics = [
  { id: 11, title: "Listening", description: "Hear the concern fully." },
  { id: 12, title: "Escalation", description: "Know when to hand over." }
];

const questions = [
  {
    id: 21,
    test_id: 7,
    text: "What is the best first response to an upset customer?",
    explanation: "Start by acknowledging the concern clearly.",
    difficulty: 3,
    estimated_seconds: 45,
    option_count: 4,
    options: [
      { id: 101, text: "Acknowledge the concern and ask a clarifying question", is_correct: true },
      { id: 102, text: "Tell the customer they are wrong", is_correct: false },
      { id: 103, text: "End the call quickly", is_correct: false },
      { id: 104, text: "Transfer without context", is_correct: false }
    ],
    topic_ids: [11],
    topic_titles: ["Listening"]
  }
];

function renderTestsPage() {
  return render(
    <MemoryRouter initialEntries={["/tests"]}>
      <AppTestProviders language="en">
        <TestsPage session={session} />
      </AppTestProviders>
    </MemoryRouter>
  );
}

describe("TestsPage", () => {
  beforeEach(() => {
    apiPatchMock.mockReset();
    apiPostMock.mockReset();
    apiRequestMock.mockReset();
    scrollIntoViewMock.mockReset();
    Object.defineProperty(window.HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoViewMock
    });
    apiRequestMock.mockImplementation(async (path: string) => {
      if (path === "/courses") {
        return courses;
      }
      if (path === "/tests") {
        return tests;
      }
      if (path === "/topics") {
        return topics;
      }
      if (path === "/questions?test_id=7") {
        return questions;
      }
      throw new Error(`Unexpected apiRequest path: ${path}`);
    });
  });

  it("applies presets and shows setup hints for the selected course", async () => {
    const user = userEvent.setup();

    renderTestsPage();

    expect(await screen.findByText("Recommended presets")).toBeInTheDocument();
    expect(screen.getByText("Setup summary")).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Example: "Customer service essentials - final assessment"')).toBeInTheDocument();
    expect(screen.getByText("Existing tests")).toBeInTheDocument();
    expect(screen.getByText("Questions in bank: 3")).toBeInTheDocument();
    expect(screen.getByText("Questions inside the test")).toBeInTheDocument();
    expect(await screen.findByText("What is the best first response to an upset customer?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Final assessment" }));

    await waitFor(() => expect(screen.getByLabelText("Baseline difficulty")).toHaveValue("4"));
    expect(screen.getByLabelText("Question limit")).toHaveValue(15);
    expect(screen.getAllByText("extended format")).toHaveLength(2);
  });

  it("submits the tuned adaptive parameters", async () => {
    const user = userEvent.setup();
    apiPostMock.mockResolvedValue({ id: 8, title: "New test" });

    renderTestsPage();

    await screen.findByText("Recommended presets");
    await user.click(screen.getByRole("button", { name: "Quick check" }));
    await user.type(screen.getByLabelText("Test title"), "New test");
    await user.click(screen.getByRole("button", { name: "Create test" }));

    expect(apiPostMock).toHaveBeenCalledWith("/tests", session, {
      course_id: 1,
      title: "New test",
      baseline_difficulty: 2,
      question_limit: 5
    });
  });

  it("creates a question with answer options and linked topics", async () => {
    const user = userEvent.setup();
    apiPostMock.mockResolvedValue({ id: 99 });

    renderTestsPage();

    await screen.findByText("Questions inside the test");
    await user.type(screen.getByLabelText("Question text"), "How should an agent open a difficult call?");
    await user.clear(screen.getByLabelText("Expected answer time, sec"));
    await user.type(screen.getByLabelText("Expected answer time, sec"), "60");
    await user.click(screen.getByLabelText("Listening"));

    const optionInputs = screen.getAllByPlaceholderText(/Option /);
    await user.type(optionInputs[0], "Acknowledge the issue calmly");
    await user.type(optionInputs[1], "Interrupt quickly");
    await user.type(optionInputs[2], "Transfer without context");
    await user.type(optionInputs[3], "Promise anything");

    await user.click(screen.getByRole("button", { name: "Add question" }));

    expect(apiPostMock).toHaveBeenCalledWith("/questions", session, {
      test_id: 7,
      text: "How should an agent open a difficult call?",
      explanation: "",
      difficulty: 3,
      estimated_seconds: 60,
      topic_ids: [11],
      options: [
        { text: "Acknowledge the issue calmly", is_correct: true },
        { text: "Interrupt quickly", is_correct: false },
        { text: "Transfer without context", is_correct: false },
        { text: "Promise anything", is_correct: false }
      ]
    });
  });

  it("loads an existing question into the form and saves edits", async () => {
    const user = userEvent.setup();
    apiPatchMock.mockResolvedValue({ id: 21 });

    renderTestsPage();

    await screen.findByText("What is the best first response to an upset customer?");
    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(scrollIntoViewMock).toHaveBeenCalled();
    await waitFor(() => expect(screen.getByDisplayValue("What is the best first response to an upset customer?")).toBeInTheDocument());
    expect(screen.getByDisplayValue("Acknowledge the concern and ask a clarifying question")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Post-answer explanation"));
    await user.type(screen.getByLabelText("Post-answer explanation"), "Lead with empathy and then gather details.");
    await user.click(screen.getByRole("button", { name: "Save question" }));

    expect(apiPatchMock).toHaveBeenCalled();
    const [path, requestSession, payload] = apiPatchMock.mock.calls[0];
    expect(path).toBe("/questions/21");
    expect(requestSession).toEqual(session);
    expect(payload).toMatchObject({
      test_id: 7,
      difficulty: 3,
      estimated_seconds: 45,
      topic_ids: [11],
      options: [
        { text: "Acknowledge the concern and ask a clarifying question", is_correct: true },
        { text: "Tell the customer they are wrong", is_correct: false },
        { text: "End the call quickly", is_correct: false },
        { text: "Transfer without context", is_correct: false }
      ]
    });
    expect(payload.text).toContain("What is the best first response to an upset customer?");
    expect(payload.explanation).toContain("Lead");
  });
});
