export type ApiResponse<T = unknown> = {
  code: number;
  message: string;
  request_id: string;
  data: T;
};

export type KnowledgeSourceItem = {
  id: string;
  name: string;
  type: string;
  status: string;
  last_synced_at?: string | null;
};

export type HandoffQueueItem = {
  id: string;
  session_id: string;
  status: string;
  reason?: string;
  assignee_id?: string | null;
  created_at?: string;
};

export type KnowledgeSourceCreateInput = {
  type: string;
  name: string;
  config: Record<string, unknown>;
  tags: string[];
};

export type HandoffReplyInput = {
  content: string;
  mark_as_kb_candidate: boolean;
};

export type KbCandidateItem = {
  id: string;
  question: string;
  answer?: string;
  status: string;
};

export type CandidateRejectInput = {
  reason?: string;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type LoginData = {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    name: string;
    role: string;
    tenant_id: string;
  };
};

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:18000";
const TOKEN_KEY = "tm_access_token";
const REFRESH_TOKEN_KEY = "tm_refresh_token";
const AUTH_EXPIRED_EVENT = "tm-auth-expired";

export class ApiError extends Error {
  status: number;
  detail?: string;
  requestId?: string;
  code?: number;
  path?: string;

  constructor(
    status: number,
    message: string,
    detail?: string,
    requestId?: string,
    code?: number,
    path?: string
  ) {
    super(message);
    this.status = status;
    this.detail = detail;
    this.requestId = requestId;
    this.code = code;
    this.path = path;
  }
}

async function doRequest<T>(path: string, init?: RequestInit): Promise<Response> {
  const token = localStorage.getItem(TOKEN_KEY);
  return fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
}

let refreshingPromise: Promise<void> | null = null;

async function refreshAccessToken(): Promise<void> {
  if (refreshingPromise) {
    return refreshingPromise;
  }
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    throw new Error("missing refresh token");
  }
  refreshingPromise = (async () => {
    const res = await fetch(`${BASE_URL}/api/v1/tm/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      throw new Error("refresh token failed");
    }
    const payload = (await res.json()) as ApiResponse<{ access_token: string; refresh_token: string }>;
    if (!payload.data?.access_token || !payload.data?.refresh_token) {
      throw new Error("refresh response missing tokens");
    }
    setAuthTokens(payload.data.access_token, payload.data.refresh_token);
  })();
  try {
    await refreshingPromise;
  } finally {
    refreshingPromise = null;
  }
}

async function request<T>(path: string, init?: RequestInit, allowRefresh = true): Promise<ApiResponse<T>> {
  let res = await doRequest<T>(path, init);
  if (
    res.status === 401 &&
    allowRefresh &&
    path !== "/api/v1/tm/auth/login" &&
    path !== "/api/v1/tm/auth/refresh"
  ) {
    try {
      await refreshAccessToken();
      res = await doRequest<T>(path, init);
    } catch {
      clearAccessToken();
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }
  }
  if (!res.ok) {
    let detail = "";
    let requestId = "";
    let message = `HTTP ${res.status}`;
    let code: number | undefined;
    try {
      const payload = await res.json();
      detail = payload?.detail ?? payload?.message ?? "";
      requestId = payload?.request_id ?? "";
      message = payload?.message ?? message;
      code = typeof payload?.code === "number" ? payload.code : undefined;
    } catch {
      detail = "";
    }
    if (res.status === 401) {
      clearAccessToken();
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }
    throw new ApiError(res.status, message, detail, requestId, code, path);
  }
  return (await res.json()) as ApiResponse<T>;
}

export function getHealth() {
  return request<{ status: string }>("/api/v1/tm/health");
}

export function login(payload: LoginInput) {
  return request<LoginData>("/api/v1/tm/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMe() {
  return request<{
    id: string;
    name: string;
    role: string;
    tenant_id: string;
    email: string;
  }>("/api/v1/tm/auth/me");
}

export function setAccessToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function setAuthTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearAccessToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function onAuthExpired(handler: () => void) {
  window.addEventListener(AUTH_EXPIRED_EVENT, handler);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handler);
}

export function getKnowledgeSources() {
  return request<{
    list?: KnowledgeSourceItem[];
    items?: KnowledgeSourceItem[];
  }>("/api/v1/tm/knowledge-sources");
}

export function getHandoffQueue() {
  return request<{
    list?: HandoffQueueItem[];
    items?: HandoffQueueItem[];
  }>("/api/v1/tm/handoff/queue");
}

export function createKnowledgeSource(payload: KnowledgeSourceCreateInput) {
  return request("/api/v1/tm/knowledge-sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function claimHandoff(handoffId: string) {
  return request(`/api/v1/tm/handoff/queue/${handoffId}/claim`, {
    method: "POST",
  });
}

export function closeHandoff(handoffId: string) {
  return request(`/api/v1/tm/handoff/queue/${handoffId}/close`, {
    method: "POST",
  });
}

export function replyHandoff(handoffId: string, payload: HandoffReplyInput) {
  return request(`/api/v1/tm/handoff/queue/${handoffId}/reply`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getKbCandidates(status?: string) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<{
    list?: KbCandidateItem[];
    items?: KbCandidateItem[];
  }>(`/api/v1/tm/kb-candidates${query}`);
}

export function approveKbCandidate(candidateId: string) {
  return request(`/api/v1/tm/kb-candidates/${candidateId}/approve`, {
    method: "POST",
  });
}

export function rejectKbCandidate(candidateId: string, payload: CandidateRejectInput) {
  return request(`/api/v1/tm/kb-candidates/${candidateId}/reject`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
