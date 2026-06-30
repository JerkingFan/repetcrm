import { api, ApiError } from "@/lib/api";

export const JOB_POLL_INTERVAL_MS = 1500;
export const JOB_TIMEOUT_MS = 3 * 60_000;

export type JobPollResult = {
  ok: boolean;
  result?: Record<string, unknown> | null;
  error?: string;
};

export async function pollJobUntilDone(
  token: string,
  jobId: string,
  onStatus?: (status: string) => void
): Promise<JobPollResult> {
  const deadline = Date.now() + JOB_TIMEOUT_MS;

  while (Date.now() < deadline) {
    try {
      const j = await api.lessons.getJob(token, jobId);
      onStatus?.(j.status);
      if (j.status === "done") {
        return { ok: true, result: j.result ?? null };
      }
      if (j.status === "error") {
        return { ok: false, error: j.error || "Ошибка выполнения задачи" };
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        return {
          ok: false,
          error: "Задача не найдена (сервер перезапущен). Нажмите «Сгенерировать» снова.",
        };
      }
    }
    await new Promise((r) => setTimeout(r, JOB_POLL_INTERVAL_MS));
  }

  return {
    ok: false,
    error: "Превышено время ожидания (3 мин). Попробуйте снова.",
  };
}
