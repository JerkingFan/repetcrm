import { getApiUrl } from "@/lib/apiUrl";
import { clearToken, getToken, setToken } from "@/lib/auth";

export type StudentListItem = {
  id: number;
  name: string;
  subject: string;
  grade: string;
  school: string;
  contact: string;
  parent_contact: string;
  notes: string;
  boundary_mode?: string;
};

export type StudentListPage = {
  items: StudentListItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
};

export type StudentRecord = StudentListItem & {
  created_at: string;
  boundary_mode?: string;
  boundary_reason?: string;
  boundary_updated_at?: string | null;
};

export type BoundarySyncOut = {
  previous_mode: string;
  new_mode: string;
  mode_changed: boolean;
  escalated: boolean;
  reason: string;
  message: string | null;
};

export type LessonWithBoundarySync<TLesson = unknown> = {
  lesson: TLesson;
  boundary_sync: BoundarySyncOut | null;
};

export type LessonListItem = {
  id: number;
  student_id: number;
  board_id?: number | null;
  lesson_date: string;
  lesson_time: string;
  duration_minutes: number;
  payment_amount: number;
  is_paid: boolean;
  is_conducted?: boolean;
  status?: string;
  notes?: string;
  student_name?: string;
  homework_id?: number | null;
};

export type StudentBoundaries = {
  student_id: number;
  student_name: string;
  boundary_mode: string;
  boundary_reason: string;
  boundary_updated_at: string | null;
  suggested_mode: string;
  suggested_reason: string;
  signals: Record<string, number>;
  rules: {
    reschedule_notice: string;
    payment: string;
    slots: string;
  };
  notification_message: string | null;
};

export type BoundaryMessage = {
  student_id: number;
  student_name: string;
  mode: string;
  reason: string;
  rules: StudentBoundaries["rules"];
  message: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${getApiUrl()}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        clearToken();
        return null;
      }
      const data = (await res.json()) as { access_token: string };
      setToken(data.access_token);
      return data.access_token;
    } catch {
      clearToken();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
  retried = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const authToken = token ?? getToken();
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const res = await fetch(`${getApiUrl()}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && !retried && !path.startsWith("/auth/login") && !path.startsWith("/auth/register")) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return request<T>(path, options, newToken, true);
    }
  }

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

  refresh: () => refreshAccessToken(),

  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      clearToken();
    }
  },

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
    list: (
      token: string,
      params?: { q?: string; page?: number; page_size?: number }
    ) => {
      const qs = new URLSearchParams();
      if (params?.q?.trim()) qs.set("q", params.q.trim());
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      const query = qs.toString();
      return request<StudentListPage>(`/students${query ? `?${query}` : ""}`, {}, token);
    },
    listAll: async (token: string, q?: string) => {
      const all: StudentListItem[] = [];
      let page = 1;
      let hasMore = true;
      while (hasMore) {
        const res = await api.students.list(token, { q, page, page_size: 100 });
        all.push(...res.items);
        hasMore = res.has_more;
        page += 1;
      }
      return all;
    },
    get: <T = unknown>(token: string, id: number) => request<T>(`/students/${id}`, {}, token),
    create: (token: string, data: Partial<StudentListItem> & { name: string }) =>
      request("/students", { method: "POST", body: JSON.stringify(data) }, token),
    update: (token: string, id: number, data: Partial<StudentListItem>) =>
      request(`/students/${id}`, { method: "PUT", body: JSON.stringify(data) }, token),
    delete: (token: string, id: number) =>
      request(`/students/${id}`, { method: "DELETE" }, token),
    getBoundaries: (token: string, id: number) =>
      request<StudentBoundaries>(`/students/${id}/boundaries`, {}, token),
    getBoundaryMessage: (token: string, id: number, mode?: string) => {
      const qs = mode ? `?mode=${encodeURIComponent(mode)}` : "";
      return request<BoundaryMessage>(`/students/${id}/boundaries/message${qs}`, {}, token);
    },
    applyBoundaries: (token: string, id: number, data: { mode: string; reason?: string }) =>
      request<StudentRecord>(
        `/students/${id}/boundaries/apply`,
        { method: "POST", body: JSON.stringify(data) },
        token
      ),
  },

  lessons: {
    list: (token: string, params?: { from?: string; to?: string }) => {
      const qs = new URLSearchParams();
      if (params?.from) qs.set("from", params.from);
      if (params?.to) qs.set("to", params.to);
      const query = qs.toString();
      return request<LessonListItem[]>(`/lessons${query ? `?${query}` : ""}`, {}, token);
    },
    get: <T = unknown>(token: string, id: number) => request<T>(`/lessons/${id}`, {}, token),
    startHomeworkJob: (token: string, id: number) =>
      request<{ job_id: string; status: string }>(`/lessons/${id}/generate-homework-job`, { method: "POST" }, token),
    getJob: (token: string, jobId: string) =>
      request<{
        job_id: string;
        status: "queued" | "running" | "done" | "error";
        lesson_id?: number | null;
        created_at_ms: number;
        updated_at_ms: number;
        result?: {
          homework_id?: number;
          generation_source?: string;
          generation_hint?: string;
          configured_provider?: string;
          configured_model?: string;
        } | null;
        error?: string | null;
      }>(`/jobs/${encodeURIComponent(jobId)}`, {}, token),
    create: <T = unknown>(token: string, data: object) =>
      request<T>("/lessons", { method: "POST", body: JSON.stringify(data) }, token),
    update: <T = unknown>(token: string, id: number, data: object) =>
      request<T>(`/lessons/${id}`, { method: "PUT", body: JSON.stringify(data) }, token),
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
    // legacy synchronous endpoint (kept for compatibility / debugging)
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
