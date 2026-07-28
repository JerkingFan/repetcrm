"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import ConfettiBurst from "./ConfettiBurst";
import { PortalCard } from "./PortalShell";

type DailyPayload = Awaited<ReturnType<typeof api.portal.daily>>;

export default function PortalDailyChallenge({
  onSolved,
}: {
  onSolved?: () => void;
}) {
  const [data, setData] = useState<DailyPayload | null>(null);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [celebrate, setCelebrate] = useState(false);

  const load = () => {
    api.portal
      .daily()
      .then(setData)
      .catch(() => setData(null));
  };

  useEffect(() => {
    load();
  }, []);

  if (!data) return null;

  if (!data.available || !data.challenge) {
    if (data.reason === "lesson_today") {
      return (
        <PortalCard className="p-4 border-emerald-200/80 bg-emerald-50/50">
          <p className="text-[11px] uppercase tracking-wide text-emerald-800 font-semibold">
            Сегодня урок
          </p>
          <p className="text-sm text-emerald-950 mt-1">
            День без случайного задания — стрик держи сдачей ДЗ после занятия.
          </p>
        </PortalCard>
      );
    }
    return null;
  }

  const ch = data.challenge;
  const solved = ch.status === "correct";
  const canRetry = ch.status !== "correct";

  const submit = async () => {
    if (!answer.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.portal.answerDaily(ch.id, answer.trim());
      setData(res);
      if (res.challenge?.status === "correct") {
        setCelebrate(true);
        onSolved?.();
      } else {
        setAnswer("");
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось проверить");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <ConfettiBurst active={celebrate} />
      <PortalCard className="overflow-hidden border-violet-200/80">
        <div className="bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-3 text-white">
          <p className="text-[11px] uppercase tracking-wide text-white/75 font-semibold">
            Задание дня
          </p>
          <p className="font-bold mt-0.5">{ch.topic || "Мини-практика"}</p>
          <p className="text-xs text-white/80 mt-1">Закрой стрик без урока — впиши ответ</p>
        </div>
        <div className="p-4 space-y-3">
          <p className="text-sm font-medium text-slate-900 leading-relaxed">{ch.question}</p>

          {solved ? (
            <div className="rounded-xl border p-3 text-sm bg-emerald-50 border-emerald-200 text-emerald-950">
              <p className="font-bold">
                Верно — стрик засчитан 🔥
                {ch.ai_score != null ? ` · ${ch.ai_score}%` : ""}
              </p>
              {ch.ai_feedback && <p className="mt-1.5 leading-relaxed">{ch.ai_feedback}</p>}
              {ch.answer_text && (
                <p className="mt-2 text-xs opacity-70">Твой ответ: {ch.answer_text}</p>
              )}
            </div>
          ) : (
            <>
              {ch.status === "incorrect" && (
                <div className="rounded-xl border p-3 text-sm bg-amber-50 border-amber-200 text-amber-950">
                  <p className="font-bold">
                    Пока неверно
                    {ch.ai_score != null ? ` · ${ch.ai_score}%` : ""}
                  </p>
                  {ch.ai_feedback && <p className="mt-1.5 leading-relaxed">{ch.ai_feedback}</p>}
                  <p className="mt-1.5 text-xs opacity-80">Можно попробовать ещё раз</p>
                </div>
              )}
              {canRetry && (
                <>
                  <input
                    type="text"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submit();
                    }}
                    placeholder="Твой ответ…"
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-sm"
                  />
                  {error && <p className="text-xs text-rose-600">{error}</p>}
                  <button
                    type="button"
                    disabled={busy || !answer.trim()}
                    onClick={submit}
                    className="w-full py-2.5 rounded-xl bg-violet-600 text-white text-sm font-semibold disabled:opacity-50"
                  >
                    {busy ? "Проверяем…" : ch.status === "incorrect" ? "Попробовать снова" : "Проверить"}
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </PortalCard>
    </>
  );
}
