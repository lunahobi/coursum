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

const CP1251_EXTRA: Record<string, number> = {
  "\u0402": 0x80,
  "\u0403": 0x81,
  "\u201a": 0x82,
  "\u0453": 0x83,
  "\u201e": 0x84,
  "\u2026": 0x85,
  "\u2020": 0x86,
  "\u2021": 0x87,
  "\u20ac": 0x88,
  "\u2030": 0x89,
  "\u0409": 0x8a,
  "\u2039": 0x8b,
  "\u040a": 0x8c,
  "\u040c": 0x8d,
  "\u040b": 0x8e,
  "\u040f": 0x8f,
  "\u0452": 0x90,
  "\u2018": 0x91,
  "\u2019": 0x92,
  "\u201c": 0x93,
  "\u201d": 0x94,
  "\u2022": 0x95,
  "\u2013": 0x96,
  "\u2014": 0x97,
  "\u2122": 0x99,
  "\u0459": 0x9a,
  "\u203a": 0x9b,
  "\u045a": 0x9c,
  "\u045c": 0x9d,
  "\u045b": 0x9e,
  "\u045f": 0x9f,
  "\u00a0": 0xa0,
  "\u040e": 0xa1,
  "\u045e": 0xa2,
  "\u0408": 0xa3,
  "\u00a4": 0xa4,
  "\u0490": 0xa5,
  "\u00a6": 0xa6,
  "\u00a7": 0xa7,
  "\u0401": 0xa8,
  "\u00a9": 0xa9,
  "\u0404": 0xaa,
  "\u00ab": 0xab,
  "\u00ac": 0xac,
  "\u00ad": 0xad,
  "\u00ae": 0xae,
  "\u0407": 0xaf,
  "\u00b0": 0xb0,
  "\u00b1": 0xb1,
  "\u0406": 0xb2,
  "\u0456": 0xb3,
  "\u0491": 0xb4,
  "\u00b5": 0xb5,
  "\u00b6": 0xb6,
  "\u00b7": 0xb7,
  "\u0451": 0xb8,
  "\u2116": 0xb9,
  "\u0454": 0xba,
  "\u00bb": 0xbb,
  "\u0458": 0xbc,
  "\u0405": 0xbd,
  "\u0455": 0xbe,
  "\u0457": 0xbf
};

const WINDOWS_1252_ALIAS: Record<string, number> = {
  "\u20ac": 0x80,
  "\u0081": 0x81,
  "\u201a": 0x82,
  "\u0192": 0x83,
  "\u201e": 0x84,
  "\u2026": 0x85,
  "\u2020": 0x86,
  "\u2021": 0x87,
  "\u02c6": 0x88,
  "\u2030": 0x89,
  "\u0160": 0x8a,
  "\u2039": 0x8b,
  "\u0152": 0x8c,
  "\u008d": 0x8d,
  "\u017d": 0x8e,
  "\u008f": 0x8f,
  "\u0090": 0x90,
  "\u2018": 0x91,
  "\u2019": 0x92,
  "\u201c": 0x93,
  "\u201d": 0x94,
  "\u2022": 0x95,
  "\u2013": 0x96,
  "\u2014": 0x97,
  "\u02dc": 0x98,
  "\u2122": 0x99,
  "\u0161": 0x9a,
  "\u203a": 0x9b,
  "\u0153": 0x9c,
  "\u009d": 0x9d,
  "\u017e": 0x9e,
  "\u0178": 0x9f
};

function encodeCp1251(value: string) {
  const bytes: number[] = [];
  for (const char of value) {
    const code = char.charCodeAt(0);
    if (code <= 0x7f) {
      bytes.push(code);
      continue;
    }
    if (code >= 0x80 && code <= 0x9f) {
      bytes.push(code);
      continue;
    }
    if (char === "\u0401") {
      bytes.push(0xa8);
      continue;
    }
    if (char === "\u0451") {
      bytes.push(0xb8);
      continue;
    }
    if (code >= 0x0410 && code <= 0x042f) {
      bytes.push(code - 0x0410 + 0xc0);
      continue;
    }
    if (code >= 0x0430 && code <= 0x044f) {
      bytes.push(code - 0x0430 + 0xe0);
      continue;
    }
    if (char in CP1251_EXTRA) {
      bytes.push(CP1251_EXTRA[char]);
      continue;
    }
    if (char in WINDOWS_1252_ALIAS) {
      bytes.push(WINDOWS_1252_ALIAS[char]);
      continue;
    }
    return null;
  }
  return new Uint8Array(bytes);
}

function repairMojibakeText(value: string) {
  if (!value) {
    return value;
  }
  let repaired = value;
  for (let step = 0; step < 2; step += 1) {
    const bytes = encodeCp1251(repaired);
    if (!bytes) {
      return repaired;
    }
    try {
      const next = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      if (next === repaired) {
        break;
      }
      repaired = next;
    } catch {
      return repaired;
    }
  }
  return repaired;
}

function repairPayload<T>(value: T): T {
  if (typeof value === "string") {
    return repairMojibakeText(value) as T;
  }
  if (Array.isArray(value)) {
    return value.map((item) => repairPayload(item)) as T;
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, repairPayload(item)])
    ) as T;
  }
  return value;
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
    return repairPayload(JSON.parse(text));
  } catch {
    return repairPayload(text);
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
      body: JSON.stringify({ refresh_token: key })
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
    !authRetryDone &&
    session?.refreshToken &&
    response.status === 401 &&
    !isAuthTokenEndpoint,
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
    body: JSON.stringify({ email, password })
  });
}

export async function apiPost(path: string, session: SessionState, payload: unknown) {
  return apiRequest(path, session, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function apiPatch(path: string, session: SessionState, payload: unknown) {
  return apiRequest(path, session, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function apiDelete(path: string, session: SessionState) {
  return apiRequest(path, session, {
    method: "DELETE"
  });
}

export async function apiUpload(path: string, session: SessionState, payload: FormData, onProgress?: (progress: number) => void) {
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
          payloadValue = repairPayload(JSON.parse(xhr.responseText));
        } catch {
          payloadValue = repairPayload(xhr.responseText);
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
