export type SessionState = {
  accessToken: string;
  tenantCode: string;
  refreshToken?: string;
};

type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

type SessionLifecycleHandlers = {
  onSessionUpdate?: (session: SessionState) => void;
  onSessionInvalid?: () => void;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";

function getApiOrigin() {
  try {
    return new URL(API_BASE).origin;
  } catch {
    return typeof window !== "undefined" ? window.location.origin : "";
  }
}

function extractApiErrorMessage(payload: unknown) {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }
  return "API error";
}

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(status: number, payload: unknown) {
    super(extractApiErrorMessage(payload));
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

let sessionLifecycle: SessionLifecycleHandlers = {};
const refreshRequestsInFlight = new Map<string, Promise<TokenPair>>();

export function configureSessionLifecycle(handlers: SessionLifecycleHandlers) {
  sessionLifecycle = handlers;
}

function withAuthHeaders(headers: Headers, session?: SessionState) {
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }
  if (session?.tenantCode) {
    headers.set("X-Tenant-Code", session.tenantCode);
  }
}

async function parseResponsePayload(response: Response) {
  const text = await response.text();
  if (!text.trim()) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function requestRefreshToken(refreshToken: string): Promise<TokenPair> {
  const key = refreshToken.trim();
  if (!key) {
    throw new ApiError(401, { detail: "Session expired" });
  }
  if (!refreshRequestsInFlight.has(key)) {
    const request = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: key }),
    })
      .then(async (response) => {
        const payload = await parseResponsePayload(response);
        if (!response.ok) {
          throw new ApiError(response.status, payload);
        }
        return payload as TokenPair;
      })
      .finally(() => {
        refreshRequestsInFlight.delete(key);
      });
    refreshRequestsInFlight.set(key, request);
  }
  return refreshRequestsInFlight.get(key)!;
}

async function requestWithSessionRetry(
  path: string,
  session?: SessionState,
  init?: RequestInit,
  authRetryDone = false,
) {
  const headers = new Headers(init?.headers ?? {});
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  withAuthHeaders(headers, session);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const payload = await parseResponsePayload(response);

  const isAuthTokenEndpoint = path === "/auth/login" || path === "/auth/refresh";
  const canAttemptRefresh = Boolean(
    !authRetryDone && session?.refreshToken && response.status === 401 && !isAuthTokenEndpoint,
  );

  if (canAttemptRefresh) {
    try {
      const nextTokens = await requestRefreshToken(session!.refreshToken!);
      const nextSession: SessionState = {
        ...session!,
        accessToken: nextTokens.access_token,
        refreshToken: nextTokens.refresh_token,
      };
      sessionLifecycle.onSessionUpdate?.(nextSession);
      return requestWithSessionRetry(path, nextSession, init, true);
    } catch (refreshError) {
      sessionLifecycle.onSessionInvalid?.();
      if (refreshError instanceof ApiError) {
        throw refreshError;
      }
      throw new ApiError(401, { detail: "Session expired" });
    }
  }

  if (!response.ok) {
    if (response.status === 401 && session && !isAuthTokenEndpoint) {
      sessionLifecycle.onSessionInvalid?.();
    }
    throw new ApiError(response.status, payload);
  }

  return payload;
}

export async function apiRequest(path: string, session?: SessionState, init?: RequestInit) {
  return requestWithSessionRetry(path, session, init);
}

export async function login(email: string, password: string) {
  return apiRequest("/auth/login", undefined, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function apiPost(path: string, session: SessionState, payload: unknown) {
  return apiRequest(path, session, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function apiPatch(path: string, session: SessionState, payload: unknown) {
  return apiRequest(path, session, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function apiDelete(path: string, session: SessionState) {
  return apiRequest(path, session, {
    method: "DELETE",
  });
}

export async function apiUpload(
  path: string,
  session: SessionState,
  payload: FormData,
  onProgress?: (progress: number) => void,
) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    if (session.accessToken) xhr.setRequestHeader("Authorization", `Bearer ${session.accessToken}`);
    if (session.tenantCode) xhr.setRequestHeader("X-Tenant-Code", session.tenantCode);
    xhr.upload.onprogress = (event) => {
      if (!onProgress || !event.lengthComputable) {
        return;
      }
      onProgress(Math.max(0, Math.min(100, Math.round((event.loaded / event.total) * 100))));
    };
    xhr.onerror = () => {
      reject(new Error("Network error"));
    };
    xhr.onabort = () => {
      reject(new Error("Upload cancelled"));
    };
    xhr.onload = () => {
      let payloadValue: unknown = {};
      if (xhr.responseText) {
        try {
          payloadValue = JSON.parse(xhr.responseText);
        } catch {
          payloadValue = xhr.responseText;
        }
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100);
        resolve(payloadValue);
        return;
      }
      if (xhr.status === 401 && session.refreshToken) {
        requestRefreshToken(session.refreshToken)
          .then((nextTokens) => {
            const nextSession: SessionState = {
              ...session,
              accessToken: nextTokens.access_token,
              refreshToken: nextTokens.refresh_token,
            };
            sessionLifecycle.onSessionUpdate?.(nextSession);
            return apiUpload(path, nextSession, payload, onProgress).then(resolve, reject);
          })
          .catch((refreshError) => {
            sessionLifecycle.onSessionInvalid?.();
            if (refreshError instanceof Error) {
              reject(refreshError);
              return;
            }
            reject(new ApiError(401, { detail: "Session expired" }));
          });
        return;
      }
      reject(new ApiError(xhr.status, payloadValue));
    };
    xhr.send(payload);
  });
}

export function resolveMediaUrl(url: string) {
  if (!url) {
    return url;
  }
  if (/^(https?:|blob:|data:)/i.test(url)) {
    return url;
  }
  if (url.startsWith("/")) {
    return `${getApiOrigin()}${url}`;
  }
  return url;
}
