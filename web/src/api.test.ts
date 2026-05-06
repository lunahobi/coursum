import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest, configureSessionLifecycle, SessionState } from "./api";

const session: SessionState = {
  accessToken: "access-token",
  refreshToken: "refresh-token",
  tenantCode: "tenant-a"
};

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

describe("session refresh lifecycle", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    configureSessionLifecycle({});
  });

  it("refreshes the access token after 401 and retries request", async () => {
    const onSessionUpdate = vi.fn();
    configureSessionLifecycle({ onSessionUpdate });

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "Access token expired" }, 401))
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "next-access-token",
          refresh_token: "next-refresh-token",
          token_type: "bearer"
        })
      )
      .mockResolvedValueOnce(jsonResponse({ ok: true }));

    const payload = await apiRequest("/courses", session);
    expect(payload).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(onSessionUpdate).toHaveBeenCalledWith({
      ...session,
      accessToken: "next-access-token",
      refreshToken: "next-refresh-token"
    });
  });

  it("invalidates session when refresh token is rejected", async () => {
    const onSessionInvalid = vi.fn();
    configureSessionLifecycle({ onSessionInvalid });

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ detail: "Access token expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: "Invalid refresh token" }, 401));

    await expect(apiRequest("/courses", session)).rejects.toMatchObject({ status: 401 });
    expect(onSessionInvalid).toHaveBeenCalledTimes(1);
  });

  it("keeps refresh retries isolated by refresh token", async () => {
    const sessionA: SessionState = {
      accessToken: "access-a",
      refreshToken: "refresh-a",
      tenantCode: "tenant-a",
    };
    const sessionB: SessionState = {
      accessToken: "access-b",
      refreshToken: "refresh-b",
      tenantCode: "tenant-b",
    };
    const onSessionUpdate = vi.fn();
    configureSessionLifecycle({ onSessionUpdate });

    vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(async () => jsonResponse({ detail: "Expired A" }, 401))
      .mockImplementationOnce(async () => jsonResponse({ detail: "Expired B" }, 401))
      .mockImplementationOnce(async () =>
        jsonResponse({
          access_token: "new-access-a",
          refresh_token: "new-refresh-a",
          token_type: "bearer",
        }),
      )
      .mockImplementationOnce(async () =>
        jsonResponse({
          access_token: "new-access-b",
          refresh_token: "new-refresh-b",
          token_type: "bearer",
        }),
      )
      .mockImplementationOnce(async () => jsonResponse({ ok: "A" }))
      .mockImplementationOnce(async () => jsonResponse({ ok: "B" }));

    const [payloadA, payloadB] = await Promise.all([
      apiRequest("/courses", sessionA),
      apiRequest("/courses", sessionB),
    ]);

    expect(payloadA).toEqual({ ok: "A" });
    expect(payloadB).toEqual({ ok: "B" });
    expect(onSessionUpdate).toHaveBeenCalledWith({
      ...sessionA,
      accessToken: "new-access-a",
      refreshToken: "new-refresh-a",
    });
    expect(onSessionUpdate).toHaveBeenCalledWith({
      ...sessionB,
      accessToken: "new-access-b",
      refreshToken: "new-refresh-b",
    });
  });
});
