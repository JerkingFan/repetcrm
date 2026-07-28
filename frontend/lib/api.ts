import { getApiUrl } from "@/lib/apiUrl";
import { clearLegacyToken } from "@/lib/auth";

export type StudentListItem = {
  id: number;
  name: string;
  subject: string;
  grade: string;
  school: string;
  contact: string;
  parent_contact: string;
  parent_name?: string;
  parent_email?: string;
  parent_phone?: string;
  parent_notify_email?: boolean;
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
  balance?: number;
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
  series_id?: number | null;
  lesson_date: string;
  lesson_time: string;
  duration_minutes: number;
  payment_amount: number;
  is_paid: boolean;
  is_conducted?: boolean;
  status?: string;
  notes?: string;
  meeting_url?: string;
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

export type LessonCreateResult = {
  lesson: LessonListItem & { checklist_items?: unknown[] };
  series: {
    id: number;
    student_id: number;
    weekday: number;
    lesson_time: string;
    duration_minutes: number;
    payment_amount: number;
    starts_on: string;
    until_date: string | null;
    weeks_ahead: number;
    is_active: boolean;
    lessons_created: number;
  } | null;
};

export type NotificationSettings = {
  notify_email: boolean;
  notify_telegram: boolean;
  notify_lesson_tomorrow: boolean;
  notify_unpaid: boolean;
  notify_homework_ready: boolean;
  telegram_chat_id: string;
  contact_telegram?: string;
  contact_url?: string;
  hide_balance_in_portal?: boolean;
  smtp_configured: boolean;
  telegram_configured: boolean;
};

export type DashboardExtended = {
  stats: {
    students_count: number;
    lessons_this_month: number;
    payments_this_month: number;
    unpaid_total: number;
  };
  upcoming_lessons: Array<{
    id: number;
    lesson_date: string;
    lesson_time: string;
    student_id: number;
    student_name: string;
    duration_minutes: number;
    is_paid: boolean;
    payment_amount: number;
    meeting_url?: string;
  }>;
  debtors: Array<{
    student_id: number;
    student_name: string;
    unpaid_amount: number;
    unpaid_lessons: number;
  }>;
  inactive_students: Array<{
    student_id: number;
    student_name: string;
    last_lesson_date: string | null;
    days_since: number | null;
  }>;
  overdue_homework: Array<{
    lesson_id: number;
    lesson_date: string;
    student_id: number;
    student_name: string;
    days_since: number;
  }>;
  trial_lessons_this_week: Array<{
    lesson_id: number;
    student_id: number;
    student_name: string;
    lesson_date: string;
    lesson_time: string;
    is_conducted: boolean;
    student_status: string;
    conducted_lessons: number;
  }>;
  trial_followups: Array<{
    student_id: number;
    student_name: string;
    parent_name: string;
    conducted_lessons: number;
    message: string;
  }>;
  pending_payment_receipts: Array<{
    id: number;
    student_id: number;
    student_name: string;
    amount: number;
    original_filename: string;
    parent_note: string;
    created_at: string;
  }>;
};

export type StudentHomeworkItem = {
  id: number;
  lesson_id: number;
  lesson_date: string;
  preview: string;
  created_at: string;
  updated_at: string;
};

export type ImportResult = {
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
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

let refreshPromise: Promise<boolean> | null = null;

/** fetch с cookie-сессией (access + refresh HttpOnly). */
export function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  return fetch(input, { ...init, credentials: "include" });
}

async function refreshSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const res = await authFetch(`${getApiUrl()}/auth/refresh`, { method: "POST" });
      if (!res.ok) return false;
      clearLegacyToken();
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

async function portalRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${getApiUrl()}${path}`, { ...options, credentials: "include" });
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

async function parentPortalRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${getApiUrl()}${path}`, { ...options, credentials: "include" });
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(detail, res.status);
  }
  return res.json();
}

async function publicRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
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

async function request<T>(path: string, options: RequestInit = {}, retried = false): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const res = await authFetch(`${getApiUrl()}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !retried && !path.startsWith("/auth/login") && !path.startsWith("/auth/register")) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return request<T>(path, options, true);
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
    request<{ access_token: string; token_type: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  refresh: () => refreshSession(),

  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      clearLegacyToken();
    }
  },

  me: () =>
    request<{
      id: number;
      email: string;
      name: string;
      onboarding_completed: boolean;
      subjects: string[];
      grade_levels: string[];
      teaching_format: string;
    }>("/auth/me"),

  completeOnboarding: (data: { subjects: string[]; grade_levels: string[]; teaching_format?: string }) =>
    request("/auth/onboarding", { method: "POST", body: JSON.stringify(data) }),

  updateProfile: (data: { subjects?: string[]; grade_levels?: string[]; teaching_format?: string }) =>
    request("/auth/profile", { method: "PUT", body: JSON.stringify(data) }),

  forgotPassword: (email: string) =>
    publicRequest<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resetPassword: (token: string, password: string) =>
    publicRequest<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),

  changePassword: (current_password: string, new_password: string) =>
    request<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),

  getNotificationSettings: () => request<NotificationSettings>("/auth/notification-settings"),

  updateNotificationSettings: (data: Partial<NotificationSettings>) =>
    request<NotificationSettings>("/auth/notification-settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  getPaymentRequisites: () =>
    request<{ payment_details: string }>("/auth/payment-requisites"),

  updatePaymentRequisites: (payment_details: string) =>
    request<{ payment_details: string }>("/auth/payment-requisites", {
      method: "PUT",
      body: JSON.stringify({ payment_details }),
    }),

  dashboard: () =>
    request<{
      students_count: number;
      lessons_this_month: number;
      payments_this_month: number;
      unpaid_total: number;
    }>("/dashboard"),

  dashboardExtended: () => request<DashboardExtended>("/dashboard/extended"),

  students: {
    list: (params?: { q?: string; page?: number; page_size?: number }) => {
      const qs = new URLSearchParams();
      if (params?.q?.trim()) qs.set("q", params.q.trim());
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      const query = qs.toString();
      return request<StudentListPage>(`/students${query ? `?${query}` : ""}`);
    },
    listAll: async (q?: string) => {
      const all: StudentListItem[] = [];
      let page = 1;
      let hasMore = true;
      while (hasMore) {
        const res = await api.students.list({ q, page, page_size: 100 });
        all.push(...res.items);
        hasMore = res.has_more;
        page += 1;
      }
      return all;
    },
    get: <T = unknown>(id: number) => request<T>(`/students/${id}`),
    listLessons: (id: number, params?: { page?: number; page_size?: number }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      const query = qs.toString();
      return request<{
        items: Array<{ id: number; lesson_date: string; homework_id?: number | null }>;
        total: number;
        page: number;
        page_size: number;
        has_more: boolean;
      }>(`/students/${id}/lessons${query ? `?${query}` : ""}`);
    },
    create: (data: Partial<StudentListItem> & { name: string }) =>
      request("/students", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<StudentListItem>) =>
      request(`/students/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request(`/students/${id}`, { method: "DELETE" }),
    getBoundaries: (id: number) => request<StudentBoundaries>(`/students/${id}/boundaries`),
    getBoundaryMessage: (id: number, mode?: string) => {
      const qs = mode ? `?mode=${encodeURIComponent(mode)}` : "";
      return request<BoundaryMessage>(`/students/${id}/boundaries/message${qs}`);
    },
    applyBoundaries: (id: number, data: { mode: string; reason?: string }) =>
      request<StudentRecord>(`/students/${id}/boundaries/apply`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    listHomework: (id: number, params?: { page?: number; page_size?: number }) => {
      const qs = new URLSearchParams();
      if (params?.page) qs.set("page", String(params.page));
      if (params?.page_size) qs.set("page_size", String(params.page_size));
      const query = qs.toString();
      return request<{
        items: StudentHomeworkItem[];
        total: number;
        page: number;
        page_size: number;
        has_more: boolean;
      }>(`/students/${id}/homework${query ? `?${query}` : ""}`);
    },
    getPortalLink: (id: number) =>
      request<{ portal_token: string; portal_url: string }>(`/students/${id}/portal-link`),
    regeneratePortalLink: (id: number) =>
      request<{ portal_token: string; portal_url: string }>(
        `/students/${id}/portal-link/regenerate`,
        { method: "POST" }
      ),
    getParentPortalLink: (id: number) =>
      request<{ parent_portal_token: string; parent_portal_url: string }>(
        `/students/${id}/parent-portal-link`
      ),
    regenerateParentPortalLink: (id: number) =>
      request<{ parent_portal_token: string; parent_portal_url: string }>(
        `/students/${id}/parent-portal-link/regenerate`,
        { method: "POST" }
      ),
    getParentReport: (id: number, month?: string) => {
      const qs = month ? `?month=${encodeURIComponent(month)}` : "";
      return request<{
        month: string;
        month_label: string;
        student_name: string;
        tutor_name: string;
        subject: string;
        grade: string;
        lessons_total: number;
        lessons_conducted: number;
        topics_covered: string[];
        payments_total: number;
        balance: number;
        lessons: Array<{
          lesson_date: string;
          lesson_time: string;
          is_conducted: boolean;
          is_paid: boolean;
          payment_amount: number;
        }>;
        homework: Array<{ lesson_date: string; status: string; status_label: string }>;
      }>(`/students/${id}/parent-report${qs}`);
    },
    parentReportPdfUrl: (id: number, month?: string) => {
      const qs = month ? `?month=${encodeURIComponent(month)}` : "";
      return `${getApiUrl()}/students/${id}/parent-report.pdf${qs}`;
    },
    sendParentReport: (id: number, month?: string) => {
      const qs = month ? `?month=${encodeURIComponent(month)}` : "";
      return request<{ message: string }>(`/students/${id}/parent-report/send${qs}`, {
        method: "POST",
      });
    },
    trialFollowup: (id: number) =>
      request<{
        show: boolean;
        message: string;
        parent_portal_url: string;
        student_name: string;
        conducted_lessons: number;
      }>(`/students/${id}/trial-followup`),
    listPackages: (id: number) =>
      request<
        Array<{
          id: number;
          student_id: number;
          name: string;
          lessons_total: number;
          lessons_remaining: number;
          price_per_lesson: number;
          is_active: boolean;
          created_at: string;
        }>
      >(`/students/${id}/packages`),
    createPackage: (
      id: number,
      data: { name: string; lessons_total: number; price_per_lesson: number; prepaid_amount?: number }
    ) =>
      request(`/students/${id}/packages`, { method: "POST", body: JSON.stringify(data) }),
    topUpBalance: (id: number, amount: number) =>
      request<StudentRecord>(`/students/${id}/balance`, {
        method: "POST",
        body: JSON.stringify({ amount }),
      }),
  },

  lessons: {
    list: (params?: {
      from?: string;
      to?: string;
      student_id?: number;
      is_paid?: boolean;
      is_conducted?: boolean;
      status?: string;
    }) => {
      const qs = new URLSearchParams();
      if (params?.from) qs.set("from", params.from);
      if (params?.to) qs.set("to", params.to);
      if (params?.student_id) qs.set("student_id", String(params.student_id));
      if (params?.is_paid !== undefined) qs.set("is_paid", params.is_paid ? "true" : "false");
      if (params?.is_conducted !== undefined)
        qs.set("is_conducted", params.is_conducted ? "true" : "false");
      if (params?.status) qs.set("status", params.status);
      const query = qs.toString();
      return request<LessonListItem[]>(`/lessons${query ? `?${query}` : ""}`);
    },
    get: <T = unknown>(id: number) => request<T>(`/lessons/${id}`),
    startHomeworkJob: (id: number) =>
      request<{ job_id: string; status: string }>(`/lessons/${id}/generate-homework-job`, {
        method: "POST",
      }),
    getJob: (jobId: string) =>
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
      }>(`/jobs/${encodeURIComponent(jobId)}`),
    create: (data: object) =>
      request<LessonCreateResult>("/lessons", { method: "POST", body: JSON.stringify(data) }),
    update: <T = unknown>(id: number, data: object) =>
      request<T>(`/lessons/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    togglePaid: (id: number, is_paid: boolean) =>
      request(`/lessons/${id}`, { method: "PUT", body: JSON.stringify({ is_paid }) }),
    delete: (id: number) => request(`/lessons/${id}`, { method: "DELETE" }),
    saveChecklist: (id: number, items: object[]) =>
      request(`/lessons/${id}/checklist`, {
        method: "POST",
        body: JSON.stringify({ items }),
      }),
    saveLessonReport: (id: number, data: { items: object[]; prefs: object; is_conducted?: boolean }) =>
      request(`/lessons/${id}/lesson-report`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    quickConduct: (id: number) =>
      request<{
        lesson_id: number;
        is_conducted: boolean;
        trial_followup: {
          show: boolean;
          message: string;
          parent_portal_url: string;
          student_name: string;
          conducted_lessons: number;
        } | null;
      }>(`/lessons/${id}/quick-conduct`, { method: "POST" }),
    generateHomework: <T = unknown>(id: number) =>
      request<T>(`/lessons/${id}/generate-homework`, { method: "POST" }),
  },

  boards: {
    list: () => request<unknown[]>(`/boards`),
    create: (title?: string) =>
      request(`/boards`, {
        method: "POST",
        body: JSON.stringify({ title }),
      }),
    get: (id: number) => request(`/boards/${id}`),
    getPublic: (id: number, shareToken: string) =>
      request(`/boards/${id}/public?token=${encodeURIComponent(shareToken)}`),
    update: (id: number, payload: { title?: string; state_json?: unknown; share_writable?: boolean }) =>
      request(`/boards/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
    updatePublic: (id: number, shareToken: string, payload: { state_json?: unknown }) =>
      request(`/boards/${id}/public?token=${encodeURIComponent(shareToken)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    wsUrl: (id: number, shareToken?: string) => {
      const base = getApiUrl();
      const httpBase =
        base.startsWith("http://") || base.startsWith("https://")
          ? base
          : `${typeof window !== "undefined" ? window.location.origin : ""}${base}`;
      const wsBase = httpBase.replace(/^http/, "ws").replace(/\/$/, "");
      const qs = new URLSearchParams();
      if (shareToken) qs.set("token", shareToken);
      const q = qs.toString();
      return `${wsBase}/boards/ws/${id}${q ? `?${q}` : ""}`;
    },
    uploadAssetUrl: (id: number, shareToken: string) =>
      `${getApiUrl()}/boards/${id}/assets?token=${encodeURIComponent(shareToken)}`,
    listSnapshots: (id: number) =>
      request<Array<{ id: number; created_at: string }>>(`/boards/${id}/snapshots`),
    restoreSnapshot: (boardId: number, snapshotId: number) =>
      request(`/boards/${boardId}/snapshots/${snapshotId}/restore`, { method: "POST" }),
  },

  data: {
    exportStudentsUrl: () => `${getApiUrl()}/data/export/students`,
    exportLessonsUrl: (params?: { from?: string; to?: string }) => {
      const qs = new URLSearchParams();
      if (params?.from) qs.set("from", params.from);
      if (params?.to) qs.set("to", params.to);
      const q = qs.toString();
      return `${getApiUrl()}/data/export/lessons${q ? `?${q}` : ""}`;
    },
    importStudents: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await authFetch(`${getApiUrl()}/data/import/students`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        let detail = "Import failed";
        try {
          const err = await res.json();
          detail = err.detail || detail;
        } catch {
          /* ignore */
        }
        throw new ApiError(detail, res.status);
      }
      return res.json() as Promise<ImportResult>;
    },
    importLessons: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await authFetch(`${getApiUrl()}/data/import/lessons`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        let detail = "Import failed";
        try {
          const err = await res.json();
          detail = err.detail || detail;
        } catch {
          /* ignore */
        }
        throw new ApiError(detail, res.status);
      }
      return res.json() as Promise<ImportResult>;
    },
  },

  calendar: {
    tutorIcsUrl: () => `${getApiUrl()}/calendar/tutor.ics`,
    studentIcsUrl: (studentId: number) => `${getApiUrl()}/calendar/student/${studentId}.ics`,
    feedIcsUrl: (portalToken: string) =>
      `${getApiUrl()}/calendar/feed.ics?token=${encodeURIComponent(portalToken)}`,
  },

  portal: {
    login: async (portal_token: string) => {
      const res = await fetch(`${getApiUrl()}/portal/session`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portal_token }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new ApiError(err.detail || "Invalid link", res.status);
      }
      return res.json() as Promise<{
        id: number;
        name: string;
        subject: string;
        grade: string;
        balance: number;
        show_balance?: boolean;
        tutor_name: string;
        tutor_telegram?: string;
        tutor_contact_url?: string;
        tutor_telegram_url?: string;
      }>;
    },
    me: () =>
      portalRequest<{
        id: number;
        name: string;
        subject: string;
        grade: string;
        balance: number;
        show_balance?: boolean;
        tutor_name: string;
        tutor_telegram?: string;
        tutor_contact_url?: string;
        tutor_telegram_url?: string;
      }>("/portal/me"),
    progress: () =>
      portalRequest<{
        homework_total: number;
        homework_submitted: number;
        homework_reviewed: number;
        homework_needs_revision: number;
        streak_days: number;
        avg_ai_score: number | null;
        topics: string[];
        recent_scores: Array<{
          homework_id: number;
          score: number;
          verdict: string;
          date: string;
        }>;
      }>("/portal/progress"),
    lessons: () =>
      portalRequest<
        Array<{
          id: number;
          lesson_date: string;
          lesson_time: string;
          duration_minutes: number;
          status: string;
          is_conducted: boolean;
          notes: string;
          meeting_url?: string;
          board_id?: number | null;
          board_url?: string;
          board_title?: string;
          can_request_reschedule?: boolean;
          reschedule_status?: string;
        }>
      >("/portal/lessons"),
    homework: () =>
      portalRequest<
        Array<{
          id: number;
          lesson_id: number;
          lesson_date: string;
          preview: string;
          tasks_count?: number;
          due_date?: string | null;
          has_submission: boolean;
          submission_status?: string;
          updated_at: string;
        }>
      >("/portal/homework"),
    homeworkDetail: (id: number) =>
      portalRequest<{
        id: number;
        lesson_id: number;
        lesson_date: string;
        homework_text: string;
        preview_html?: string;
        due_date?: string | null;
        has_submission: boolean;
        board_url?: string;
        meeting_url?: string;
        tutor_telegram_url?: string;
        submissions: Array<{
          id: number;
          original_filename: string;
          submitted_at: string;
          status?: string;
          comment?: string;
          tutor_comment?: string;
          ai_review_status?: string;
          ai_verdict?: string;
          ai_score?: number | null;
          ai_feedback?: string;
          ai_review_error?: string;
        }>;
      }>(`/portal/homework/${id}`),
    submitHomework: async (homeworkId: number, file: File, comment?: string) => {
      const form = new FormData();
      form.append("file", file);
      if (comment) form.append("comment", comment);
      const res = await fetch(`${getApiUrl()}/portal/homework/${homeworkId}/submit`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new ApiError(err.detail || "Upload failed", res.status);
      }
      return res.json();
    },
    requestReschedule: (data: {
      lesson_id: number;
      message?: string;
      preferred_date?: string | null;
      preferred_time?: string;
    }) =>
      portalRequest<{
        id: number;
        lesson_id: number;
        status: string;
        message: string;
        preferred_date?: string | null;
        preferred_time?: string;
        created_at: string;
      }>("/portal/reschedule", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    calendarIcsUrl: () => `${getApiUrl()}/portal/calendar.ics`,
    createPaymentIntent: (amount: number, provider: "erip" | "card") =>
      portalRequest<{
        id: number;
        amount: number;
        provider: string;
        status: string;
        erip_code?: string;
        payment_url?: string;
        public_token: string;
      }>("/portal/payments/intent", {
        method: "POST",
        body: JSON.stringify({ amount, provider }),
      }),
    logout: () =>
      fetch(`${getApiUrl()}/portal/logout`, { method: "POST", credentials: "include" }),
  },

  reschedule: {
    list: (status = "pending") =>
      request<
        Array<{
          id: number;
          lesson_id: number;
          student_id: number;
          student_name: string;
          lesson_date: string;
          lesson_time: string;
          message: string;
          preferred_date?: string | null;
          preferred_time?: string;
          status: string;
          tutor_note: string;
          created_at: string;
        }>
      >(`/reschedule-requests?status=${encodeURIComponent(status)}`),
    resolve: (id: number, data: { status: "approved" | "rejected"; tutor_note?: string }) =>
      request(`/reschedule-requests/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  parentPortal: {
    login: async (parent_portal_token: string) => {
      const res = await fetch(`${getApiUrl()}/parent-portal/session`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parent_portal_token }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new ApiError(err.detail || "Invalid link", res.status);
      }
      return res.json() as Promise<{
        student_id: number;
        student_name: string;
        subject: string;
        grade: string;
        parent_name: string;
        balance: number;
        tutor_name: string;
      }>;
    },
    me: () =>
      parentPortalRequest<{
        student_id: number;
        student_name: string;
        subject: string;
        grade: string;
        parent_name: string;
        balance: number;
        tutor_name: string;
      }>("/parent-portal/me"),
    lessons: () =>
      parentPortalRequest<
        Array<{
          id: number;
          lesson_date: string;
          lesson_time: string;
          duration_minutes: number;
          status: string;
          is_conducted: boolean;
          notes: string;
        }>
      >("/parent-portal/lessons"),
    packages: () =>
      parentPortalRequest<
        Array<{
          id: number;
          name: string;
          lessons_total: number;
          lessons_remaining: number;
          price_per_lesson: number;
          is_active: boolean;
        }>
      >("/parent-portal/packages"),
    homeworkStatus: () =>
      parentPortalRequest<
        Array<{
          homework_id: number;
          lesson_id: number;
          lesson_date: string;
          status: string;
          status_label: string;
          reviewed_at: string | null;
        }>
      >("/parent-portal/homework-status"),
    report: (month?: string) => {
      const qs = month ? `?month=${encodeURIComponent(month)}` : "";
      return parentPortalRequest<{
        month: string;
        month_label: string;
        student_name: string;
        tutor_name: string;
        subject: string;
        grade: string;
        lessons_total: number;
        lessons_conducted: number;
        topics_covered: string[];
        payments_total: number;
        balance: number;
        homework: Array<{ lesson_date: string; status: string; status_label: string }>;
      }>(`/parent-portal/report${qs}`);
    },
    reportPdfUrl: (month?: string) => {
      const qs = month ? `?month=${encodeURIComponent(month)}` : "";
      return `${getApiUrl()}/parent-portal/report.pdf${qs}`;
    },
    createPaymentIntent: (amount: number, provider: "erip" | "card") =>
      parentPortalRequest<{
        id: number;
        amount: number;
        provider: string;
        status: string;
        erip_code?: string;
        payment_url?: string;
        public_token: string;
      }>("/parent-portal/payments/intent", {
        method: "POST",
        body: JSON.stringify({ amount, provider }),
      }),
    paymentDetails: () =>
      parentPortalRequest<{
        tutor_name: string;
        payment_details: string;
        has_requisites: boolean;
      }>("/parent-portal/payment-details"),
    listReceipts: () =>
      parentPortalRequest<
        Array<{
          id: number;
          student_id: number;
          student_name: string;
          amount: number;
          status: string;
          original_filename: string;
          parent_note: string;
          tutor_note: string;
          created_at: string;
          reviewed_at: string | null;
        }>
      >("/parent-portal/payments/receipts"),
    submitReceipt: async (amount: number, file: File, note?: string) => {
      const form = new FormData();
      form.append("amount", String(amount));
      form.append("file", file);
      if (note) form.append("note", note);
      const res = await fetch(`${getApiUrl()}/parent-portal/payments/receipt`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new ApiError(err.detail || "Upload failed", res.status);
      }
      return res.json();
    },
    receiptFileUrl: (id: number) => `${getApiUrl()}/parent-portal/payments/receipts/${id}/file`,
    calendarFeedUrl: (parentPortalToken: string) =>
      `${getApiUrl()}/calendar/feed.ics?token=${encodeURIComponent(parentPortalToken)}`,
    calendarIcsUrl: () => `${getApiUrl()}/parent-portal/calendar.ics`,
    logout: () =>
      fetch(`${getApiUrl()}/parent-portal/logout`, { method: "POST", credentials: "include" }),
  },

  ai: {
    status: () =>
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
      }>("/ai/status"),
  },

  homework: {
    update: (
      id: number,
      homework_textOrData: string | { homework_text?: string; due_date?: string | null }
    ) => {
      const body =
        typeof homework_textOrData === "string"
          ? { homework_text: homework_textOrData }
          : homework_textOrData;
      return request(`/homework/${id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
    },
    previewHtml: (id: number) => request<{ html: string }>(`/homework/${id}/preview`),
    submissions: (id: number) =>
      request<
        Array<{
          id: number;
          homework_id: number;
          original_filename: string;
          mime_type: string;
          comment: string;
          status: string;
          tutor_comment: string;
          reviewed_at: string | null;
          ai_review_status: string;
          ai_verdict: string;
          ai_score: number | null;
          ai_feedback: string;
          ai_review_error: string;
          ai_reviewed_at: string | null;
          submitted_at: string;
        }>
      >(`/homework/${id}/submissions`),
    reviewSubmission: (
      homeworkId: number,
      submissionId: number,
      data: { status: "reviewed" | "needs_revision"; tutor_comment?: string }
    ) =>
      request(`/homework/${homeworkId}/submissions/${submissionId}/review`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    submissionFileUrl: (homeworkId: number, submissionId: number) =>
      `${getApiUrl()}/homework/${homeworkId}/submissions/${submissionId}/file`,
    pythonScriptUrl: (id: number) => `${getApiUrl()}/homework/${id}/python-script`,
    latexUrl: (id: number) => `${getApiUrl()}/homework/${id}/latex`,
    pdfUrl: (id: number) => `${getApiUrl()}/homework/${id}/pdf`,
  },

  homeworkTemplates: {
    list: () =>
      request<
        Array<{
          id: number;
          name: string;
          subject: string;
          preview: string;
          homework_text: string;
          checklist_items: Array<{
            topic: string;
            work_type: string;
            difficulty: string;
            understanding: number;
          }>;
          homework_prefs: Record<string, unknown>;
          created_at: string;
        }>
      >("/homework-templates"),
    fromLesson: (lessonId: number, name: string, includeHomeworkText = true) =>
      request(`/homework-templates/from-lesson/${lessonId}`, {
        method: "POST",
        body: JSON.stringify({ name, include_homework_text: includeHomeworkText }),
      }),
    applyToLesson: (templateId: number, lessonId: number, copyHomeworkText = true) =>
      request<{
        checklist_items: Array<{
          topic: string;
          work_type: string;
          difficulty: string;
          understanding: number;
        }>;
        homework_prefs?: Record<string, unknown>;
      }>(`/homework-templates/${templateId}/apply-to-lesson/${lessonId}`, {
        method: "POST",
        body: JSON.stringify({ copy_homework_text: copyHomeworkText }),
      }),
    delete: (id: number) => request(`/homework-templates/${id}`, { method: "DELETE" }),
  },

  payments: {
    createIntent: (data: {
      student_id: number;
      amount: number;
      provider: "erip" | "card";
      purpose?: string;
      purpose_ref_id?: number;
    }) =>
      request<{
        id: number;
        amount: number;
        provider: string;
        status: string;
        erip_code?: string;
        payment_url?: string;
        public_token: string;
      }>("/payments/intents", { method: "POST", body: JSON.stringify(data) }),
    getPublic: (token: string) =>
      fetch(`${getApiUrl()}/payments/public/${token}`).then(async (res) => {
        if (!res.ok) throw new ApiError("Not found", res.status);
        return res.json() as Promise<{
          id: number;
          amount: number;
          provider: string;
          status: string;
          erip_code?: string;
          student_name: string;
        }>;
      }),
    simulatePay: (token: string) =>
      fetch(`${getApiUrl()}/payments/public/${token}/simulate-pay`, { method: "POST" }).then(
        async (res) => {
          if (!res.ok) throw new ApiError("Payment failed", res.status);
          return res.json();
        }
      ),
  },

  analytics: {
    overview: () =>
      request<{
        revenue_by_month: Array<{ month: string; revenue: number; paid_lessons: number }>;
        trial_conversion: {
          period_days: number;
          students_with_trial_lesson: number;
          students_converted: number;
          students_with_any_lesson: number;
          conversion_rate_percent: number;
        };
        churn: {
          inactive_days_threshold: number;
          churned_students: number;
          at_risk_students: number;
          active_last_90_days: number;
          churn_rate_percent: number;
        };
      }>("/analytics/overview"),
  },

  promptTemplates: {
    list: (params?: { subject?: string; grade?: string }) => {
      const qs = new URLSearchParams();
      if (params?.subject) qs.set("subject", params.subject);
      if (params?.grade) qs.set("grade", params.grade);
      const q = qs.toString();
      return request<
        Array<{
          id: number;
          title: string;
          description: string;
          subject: string;
          grade: string;
          use_count: number;
          installed: boolean;
        }>
      >(`/prompt-templates${q ? `?${q}` : ""}`);
    },
    install: (id: number) =>
      request<{ template_id: number; homework_template_id: number; message: string }>(
        `/prompt-templates/${id}/install`,
        { method: "POST" }
      ),
  },

  paymentReceipts: {
    list: (params?: { status?: string; student_id?: number }) => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set("status", params.status);
      if (params?.student_id) qs.set("student_id", String(params.student_id));
      const q = qs.toString();
      return request<
        Array<{
          id: number;
          student_id: number;
          student_name: string;
          amount: number;
          status: string;
          original_filename: string;
          parent_note: string;
          tutor_note: string;
          created_at: string;
          reviewed_at: string | null;
        }>
      >(`/payments/receipts${q ? `?${q}` : ""}`);
    },
    fileUrl: (id: number) => `${getApiUrl()}/payments/receipts/${id}/file`,
    confirm: (id: number) =>
      request(`/payments/receipts/${id}/confirm`, { method: "POST" }),
    reject: (id: number, tutor_note?: string) =>
      request(`/payments/receipts/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ tutor_note: tutor_note || "" }),
      }),
  },

  booking: {
    getPublic: (slug: string) =>
      publicRequest<{
        tutor_name: string;
        subjects: string[];
        grade_levels: string[];
        teaching_format: string;
        slots: Array<{ date: string; time: string; label: string }>;
      }>(`/book/${encodeURIComponent(slug)}`),
    submit: (
      slug: string,
      data: {
        child_name: string;
        grade: string;
        subject: string;
        parent_name: string;
        parent_email: string;
        parent_phone?: string;
        preferred_date: string;
        preferred_time: string;
        message?: string;
      }
    ) =>
      publicRequest<{ message: string; booking_id: number }>(`/book/${encodeURIComponent(slug)}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getSettings: () =>
      request<{
        booking_slug: string;
        booking_enabled: boolean;
        booking_hours: Array<{ weekday: number; from_time: string; to_time: string }>;
        booking_reply_text: string;
        booking_url: string;
      }>("/book/settings/me"),
    updateSettings: (data: {
      booking_slug?: string;
      booking_enabled?: boolean;
      booking_hours?: Array<{ weekday: number; from_time: string; to_time: string }>;
      booking_reply_text?: string;
    }) =>
      request<{
        booking_slug: string;
        booking_enabled: boolean;
        booking_hours: Array<{ weekday: number; from_time: string; to_time: string }>;
        booking_reply_text: string;
        booking_url: string;
      }>("/book/settings/me", { method: "PUT", body: JSON.stringify(data) }),
    listLeads: () =>
      request<
        Array<{
          id: number;
          student_id: number;
          child_name: string;
          grade: string;
          subject: string;
          parent_name: string;
          parent_email: string;
          parent_phone: string;
          preferred_date: string;
          preferred_time: string;
          parent_message: string;
          status: string;
          created_at: string;
        }>
      >("/book/leads/me"),
    updateLeadStatus: (id: number, status: string) =>
      request(`/book/leads/${id}?status=${encodeURIComponent(status)}`, { method: "PATCH" }),
    publicUrl: (slug: string) => {
      const base =
        typeof window !== "undefined"
          ? window.location.origin
          : process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
      return `${base}/book/${slug}`;
    },
  },
};
