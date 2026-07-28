/** Shared labels/styles for student portal UI */

export type PortalTab = "home" | "homework" | "schedule";

export const SUBMISSION_STATUS_LABEL: Record<string, string> = {
  not_submitted: "Не сдано",
  submitted: "На проверке",
  reviewed: "Проверено",
  needs_revision: "Доработать",
};

export const AI_VERDICT_LABEL: Record<string, string> = {
  correct: "Верно",
  partially_correct: "Частично верно",
  incorrect: "Есть ошибки",
  unclear: "Не удалось оценить",
};

export function submissionChipClass(status: string): string {
  switch (status) {
    case "reviewed":
      return "bg-emerald-100 text-emerald-800";
    case "needs_revision":
      return "bg-amber-100 text-amber-900";
    case "submitted":
      return "bg-sky-100 text-sky-800";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

export function aiVerdictBoxClass(verdict: string): string {
  switch (verdict) {
    case "correct":
      return "bg-emerald-50 border-emerald-200 text-emerald-950";
    case "partially_correct":
      return "bg-amber-50 border-amber-200 text-amber-950";
    case "incorrect":
      return "bg-rose-50 border-rose-200 text-rose-950";
    default:
      return "bg-slate-50 border-slate-200 text-slate-700";
  }
}

export function formatRuDate(iso: string, opts?: Intl.DateTimeFormatOptions): string {
  return new Date(iso).toLocaleDateString("ru-RU", opts ?? { day: "numeric", month: "long" });
}

export function formatRuWeekday(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { weekday: "short" });
}

export function isToday(iso: string): boolean {
  const d = new Date(iso);
  const t = new Date();
  return d.getFullYear() === t.getFullYear() && d.getMonth() === t.getMonth() && d.getDate() === t.getDate();
}

export function isSoon(iso: string, withinDays = 2): boolean {
  const d = new Date(iso);
  d.setHours(0, 0, 0, 0);
  const t = new Date();
  t.setHours(0, 0, 0, 0);
  const diff = (d.getTime() - t.getTime()) / 86400000;
  return diff >= 0 && diff <= withinDays;
}
