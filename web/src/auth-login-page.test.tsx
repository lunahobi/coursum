import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const SAVED_ACCOUNTS_KEY = "coursum-web-saved-accounts";
const SESSION_KEY = "coursum-web-session";
const LANGUAGE_KEY = "coursum-web-language";

const { loginMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    login: loginMock,
  };
});

describe("login saved accounts", () => {
  beforeEach(() => {
    loginMock.mockReset();
    window.localStorage.clear();
    window.localStorage.setItem(LANGUAGE_KEY, "en");
  });

  function renderApp() {
    return render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
  }

  it("does not render saved-account picker in web login form", async () => {
    window.localStorage.setItem(
      SAVED_ACCOUNTS_KEY,
      JSON.stringify([
        {
          id: "tenant-a::teacher@example.com",
          organizationCode: "tenant-a",
          login: "teacher@example.com",
          lastUsedAt: new Date().toISOString(),
        },
      ]),
    );

    renderApp();

    expect(
      screen.queryByRole("button", { name: /teacher@example\.com \(tenant-a\)/i }),
    ).not.toBeInTheDocument();
  });

  it("keeps existing saved accounts and appends newly logged account", async () => {
    const user = userEvent.setup();
    const existing = {
      id: "tenant-a::teacher@example.com",
      organizationCode: "tenant-a",
      login: "teacher@example.com",
      lastUsedAt: new Date(Date.now() - 1000).toISOString(),
    };
    window.localStorage.setItem(SAVED_ACCOUNTS_KEY, JSON.stringify([existing]));
    loginMock.mockResolvedValue({
      access_token: "access-token",
      refresh_token: "refresh-token",
    });

    renderApp();

    await user.type(screen.getByPlaceholderText("Email"), "new@example.com");
    await user.type(screen.getByPlaceholderText(/Password|Пароль/i), "secret");
    const tenantInput = screen.getByPlaceholderText("Tenant code");
    await user.clear(tenantInput);
    await user.type(tenantInput, "tenant-b");
    await user.click(screen.getByRole("button", { name: /Sign in|Войти/i }));

    await waitFor(() => {
      expect(window.localStorage.getItem(SESSION_KEY)).toContain("access-token");
    });
    const raw = window.localStorage.getItem(SAVED_ACCOUNTS_KEY);
    expect(raw).toBeTruthy();
    const saved = JSON.parse(raw ?? "[]") as Array<{ id: string }>;
    expect(saved).toHaveLength(2);
    expect(saved[0].id).toBe("tenant-b::new@example.com");
    expect(saved[1].id).toBe(existing.id);
  });
});
