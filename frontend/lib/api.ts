import { getApiUrl } from "@/lib/apiUrl";

export type StudentRecord = {
  id: number;
  name: string;
  subject: string;
  grade: string;
  school: string;
  contact: string;
  parent_contact: string;
  notes: string;
  created_at: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${getApiUrl()}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const err = await res.json();
      detail = err.detail || (typeof err.detail === "string" ? err.detail : JSON.stringify(err));
      if (Array.isArray(err.detail)) detail = err.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  register: (email: string, password: string, name: string) =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: (token: string) =>
    request<{
      id: number;
      email: string;
      name: string;
      onboarding_completed: boolean;
      subjects: string[];
      grade_levels: string[];
      teaching_format: string;
    }>("/auth/me", {}, token),

  completeOnboarding: (
    token: string,
    data: { subjects: string[]; grade_levels: string[]; teaching_format?: string }
  ) =>
    request("/auth/onboarding", { method: "POST", body: JSON.stringify(data) }, token),

  updateProfile: (
    token: string,
    data: { subjects?: string[]; grade_levels?: string[]; teaching_format?: string }
  ) =>
    request("/auth/profile", { method: "PUT", body: JSON.stringify(data) }, token),

  dashboard: (token: string) =>
    request<{
      students_count: number;
      lessons_this_month: number;
      payments_this_month: number;
      unpaid_total: number;
    }>("/dashboard", {}, token),

  students: {
    list: (token: string) =>
      request<StudentRecord[]>("/students", {}, token),
    get: <T = unknown>(token: string, id: number) => request<T>(`/students/${id}`, {}, token),
    create: (token: string, data: Partial<StudentRecord> & { name: string }) =>
      request("/students", { method: "POST", body: JSON.stringify(data) }, token),
    update: (token: string, id: number, data: Partial<StudentRecord>) =>
      request(`/students/${id}`, { method: "PUT", body: JSON.stringify(data) }, token),
    delete: (token: string, id: number) =>
      request(`/students/${id}`, { method: "DELETE" }, token),
  },

  lessons: {
    list: <T = unknown>(token: string) => request<T>("/lessons", {}, token),
    get: <T = unknown>(token: string, id: number) => request<T>(`/lessons/${id}`, {}, token),
    create: <T = unknown>(token: string, data: object) =>
      request<T>("/lessons", { method: "POST", body: JSON.stringify(data) }, token),
    update: (token: string, id: number, data: object) =>
      request(`/lessons/${id}`, { method: "PUT", body: JSON.stringify(data) }, token),
    delete: (token: string, id: number) =>
      request(`/lessons/${id}`, { method: "DELETE" }, token),
    saveChecklist: (token: string, id: number, items: object[]) =>
      request(`/lessons/${id}/checklist`, {
        method: "POST",
        body: JSON.stringify({ items }),
      }, token),
    saveLessonReport: (
      token: string,
      id: number,
      data: { items: object[]; prefs: object; is_conducted?: boolean }
    ) =>
      request(`/lessons/${id}/lesson-report`, {
        method: "POST",
        body: JSON.stringify(data),
      }, token),
    generateHomework: <T = unknown>(token: string, id: number) =>
      request<T>(`/lessons/${id}/generate-homework`, { method: "POST" }, token),
  },

  boards: {
    list: (token: string) => request<unknown[]>(`/boards`, {}, token),
    create: (token: string, title?: string) =>
      request(`/boards`, {
        method: "POST",
        body: JSON.stringify({ title }),
      }, token),
    get: (token: string, id: number) => request(`/boards/${id}`, {}, token),
    getPublic: (id: number, shareToken: string) =>
      request(`/boards/${id}/public?token=${encodeURIComponent(shareToken)}`, {}),
    update: (token: string, id: number, payload: { title?: string; state_json?: unknown }) =>
      request(`/boards/${id}`, { method: "PUT", body: JSON.stringify(payload) }, token),
    updatePublic: (id: number, shareToken: string, payload: { state_json?: unknown }) =>
      request(`/boards/${id}/public?token=${encodeURIComponent(shareToken)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    wsUrl: (id: number, shareToken?: string, authToken?: string) => {
      const base = getApiUrl();
      const httpBase =
        base.startsWith("http://") || base.startsWith("https://")
          ? base
          : `${typeof window !== "undefined" ? window.location.origin : ""}${base}`;
      const wsBase = httpBase.replace(/^http/, "ws").replace(/\/$/, "");
      const qs = new URLSearchParams();
      if (shareToken) qs.set("token", shareToken);
      if (authToken) qs.set("auth", authToken);
      return `${wsBase}/boards/ws/${id}?${qs.toString()}`;
    },
    uploadAssetUrl: (id: number, shareToken: string) => `${getApiUrl()}/boards/${id}/assets?token=${encodeURIComponent(shareToken)}`,
  },

  ai: {
    status: (token: string) =>
      request<{
        ollama: {
          online: boolean;
          model_ready: boolean;
          configured_model: string;
          models: string[];
          error?: string;
        };
        local_llm: {
          available: boolean;
          path?: string;
          model_file?: string;
          eta_hint?: string;
          enabled?: boolean;
          loaded?: boolean;
        };
        recommended_setup: string;
        template_fallback_enabled: boolean;
      }>("/ai/status", {}, token),
  },

  homework: {
    update: (token: string, id: number, homework_text: string) =>
      request(`/homework/${id}`, {
        method: "PUT",
        body: JSON.stringify({ homework_text }),
      }, token),
    previewHtml: (token: string, id: number) =>
      request<{ html: string }>(`/homework/${id}/preview`, {}, token),
    pythonScriptUrl: (id: number) => `${getApiUrl()}/homework/${id}/python-script`,
    latexUrl: (id: number) => `${getApiUrl()}/homework/${id}/latex`,
    pdfUrl: (id: number) => `${getApiUrl()}/homework/${id}/pdf`,
  },
};
