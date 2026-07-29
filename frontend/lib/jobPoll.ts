import { api, ApiError } from "@/lib/api";

export const JOB_POLL_INTERVAL_MS = 1500;
/** OpenRouter: до 2 запросов × OPENROUTER_TIMEOUT_SEC (обычно 120 с) + запас */
export const JOB_TIMEOUT_MINUTES = 10;
export const JOB_TIMEOUT_MS = JOB_TIMEOUT_MINUTES * 60_000;
export const JOB_TIMEOUT_MESSAGE = `Превышено время ожидания (${JOB_TIMEOUT_MINUTES} мин). Попробуйте снова.`;

export type JobPollResult = {
  ok: boolean;
  result?: Record<string, unknown> | null;
  error?: string;
};

export async function pollJobUntilDone(
  jobId: string,
  onStatus?: (status: string) => void
): Promise<JobPollResult> {
  const deadline = Date.now() + JOB_TIMEOUT_MS;

  while (Date.now() < deadline) {
    try {
      const j = await api.lessons.getJob(jobId);
      onStatus?.(j.status);
      if (j.status === "done") {
        return { ok: true, result: j.result ?? null };
      }
      if (j.status === "error") {
        return { ok: false, error: j.error || "Ошибка выполнения задачи" };
      }
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 401 || e.status === 403) {
          return {
            ok: false,
            error: "Сессия истекла. Обновите страницу и войдите снова.",
          };
        }
        if (e.status === 404) {
          return {
            ok: false,
            error: "Задача не найдена (сервер перезапущен). Попробуйте снова.",
          };
        }
      }
    }
    await new Promise((r) => setTimeout(r, JOB_POLL_INTERVAL_MS));
  }

  return {
    ok: false,
    error: JOB_TIMEOUT_MESSAGE,
  };
}
