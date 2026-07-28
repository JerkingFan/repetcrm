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

  useEffect(() => {
    api.portal
      .daily()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return null;

  if (!data.available || !data.challenge) {
    if (data.reason === "lesson_today") {
      return (
        <PortalCard className="p-4 portal-rise border-[var(--portal-card-border)]">
          <p className="portal-kicker !text-[var(--portal-accent)]">Сегодня урок</p>
          <p className="text-sm text-slate-700 mt-1.5 leading-relaxed">
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
      <PortalCard className="overflow-hidden portal-rise">
        <div className="px-4 py-3.5 text-white relative" style={{ background: "var(--portal-hero)" }}>
          <div className="portal-hero-shine opacity-60" aria-hidden />
          <p className="relative text-[11px] uppercase tracking-[0.18em] text-white/65 font-bold">
            Задание дня
          </p>
          <p
            className="relative font-bold mt-1 text-lg tracking-tight"
            style={{ fontFamily: "var(--font-portal-display), sans-serif" }}
          >
            {ch.topic || "Мини-практика"}
          </p>
          <p className="relative text-xs text-white/75 mt-1">Закрой стрик — впиши ответ</p>
        </div>
        <div className="p-4 space-y-3">
          <p className="text-sm font-semibold text-slate-900 leading-relaxed">{ch.question}</p>

          {solved ? (
            <div className="rounded-xl border p-3.5 text-sm bg-emerald-50 border-emerald-200 text-emerald-950">
              <p className="font-bold">
                Верно — стрик засчитан
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
                <div className="rounded-xl border p-3.5 text-sm bg-amber-50 border-amber-200 text-amber-950">
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
                    className="w-full px-3.5 py-3 rounded-xl border border-slate-200/90 bg-white text-sm outline-none focus:border-[var(--portal-accent)] focus:ring-2 focus:ring-[var(--portal-accent)]/15"
                  />
                  {error && <p className="text-xs text-rose-600">{error}</p>}
                  <button
                    type="button"
                    disabled={busy || !answer.trim()}
                    onClick={submit}
                    className="portal-btn-primary w-full disabled:opacity-50"
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
