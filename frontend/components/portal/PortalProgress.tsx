"use client";

import { formatRuDate } from "@/lib/portalUi";
import { PortalCard, PortalEmpty } from "./PortalShell";

type Progress = {
  homework_total: number;
  homework_submitted: number;
  homework_reviewed: number;
  homework_needs_revision: number;
  streak_days: number;
  streak_at_risk?: boolean;
  avg_ai_score: number | null;
  topics: string[];
  topic_heat?: Array<{
    topic: string;
    avg_score: number;
    samples: number;
    level: string;
  }>;
  recent_scores: Array<{
    homework_id: number;
    score: number;
    verdict: string;
    date: string;
  }>;
  review_hint?: string;
};

function heatClass(level: string): string {
  switch (level) {
    case "strong":
      return "bg-emerald-400";
    case "ok":
      return "bg-amber-400";
    default:
      return "bg-rose-400";
  }
}

export default function PortalProgress({ data }: { data: Progress | null }) {
  if (!data) {
    return <PortalEmpty title="Загружаем прогресс…" />;
  }

  const donePct =
    data.homework_total > 0
      ? Math.round((data.homework_submitted / data.homework_total) * 100)
      : 0;
  const streak = data.streak_days;
  const atRisk = !!data.streak_at_risk && streak > 0;
  const heat = data.topic_heat || [];

  return (
    <>
      <PortalCard className="overflow-hidden">
        <div
          className={`px-5 py-5 text-white ${
            streak > 0
              ? "bg-gradient-to-br from-orange-500 via-amber-500 to-rose-500"
              : "bg-gradient-to-br from-slate-600 to-slate-800"
          }`}
        >
          <p className="text-[11px] uppercase tracking-wide text-white/75 font-semibold">Серия</p>
          <div className="flex items-end gap-3 mt-1">
            <p className={`text-5xl font-black leading-none ${streak > 0 ? "streak-pop" : ""}`}>
              {streak}
            </p>
            <div className="pb-1">
              <p className="text-lg font-bold">
                {streak === 0
                  ? "дней"
                  : streak === 1
                    ? "день подряд"
                    : streak < 5
                      ? "дня подряд"
                      : "дней подряд"}
              </p>
              <p className="text-sm text-white/85 mt-0.5">
                {streak === 0
                  ? "Сдай ДЗ сегодня — начни серию"
                  : atRisk
                    ? "Не сломай серию завтра 🔥"
                    : "Красава. Держи темп"}
              </p>
            </div>
          </div>
          {streak > 0 && (
            <div className="mt-4 flex gap-1.5">
              {Array.from({ length: Math.min(streak, 14) }).map((_, i) => (
                <span
                  key={i}
                  className="h-2 flex-1 rounded-full bg-white/90 streak-dot"
                  style={{ animationDelay: `${i * 40}ms` }}
                />
              ))}
            </div>
          )}
        </div>
      </PortalCard>

      <div className="grid grid-cols-2 gap-3">
        <PortalCard className="p-4 portal-rise">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">Сдано ДЗ</p>
          <p className="text-2xl font-bold text-brand-blue mt-1">
            {data.homework_submitted}
            <span className="text-base font-medium text-slate-400">/{data.homework_total}</span>
          </p>
          <div className="mt-2 h-1.5 rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full bg-brand-green rounded-full transition-all" style={{ width: `${donePct}%` }} />
          </div>
        </PortalCard>
        <PortalCard className="p-4 portal-rise">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">Средняя AI</p>
          <p className="text-2xl font-bold text-brand-blue mt-1">
            {data.avg_ai_score != null ? `${Math.round(data.avg_ai_score)}%` : "—"}
          </p>
          <p className="text-xs text-slate-500 mt-1">по проверенным</p>
        </PortalCard>
      </div>

      {data.review_hint && (
        <PortalCard className="p-4 border-amber-200/80 bg-amber-50/60">
          <p className="text-[11px] uppercase tracking-wide text-amber-800 font-semibold">Что повторить</p>
          <p className="text-sm text-amber-950 mt-1 font-medium">{data.review_hint}</p>
        </PortalCard>
      )}

      <PortalCard className="p-5">
        <h3 className="font-semibold text-slate-800 mb-1">Heatmap тем</h3>
        <p className="text-xs text-slate-500 mb-3">Где стабильно и где проседает (по оценкам AI)</p>
        {heat.length === 0 ? (
          <p className="text-sm text-slate-500">Сдай пару ДЗ с фото — появится карта тем</p>
        ) : (
          <ul className="space-y-2.5">
            {heat.map((t) => (
              <li key={t.topic} className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${heatClass(t.level)}`} />
                <span className="text-sm text-slate-800 flex-1 min-w-0 truncate">{t.topic}</span>
                <span className="text-xs font-semibold text-slate-500 tabular-nums">
                  {Math.round(t.avg_score)}%
                </span>
                <div className="w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden shrink-0">
                  <div
                    className={`h-full rounded-full ${heatClass(t.level)}`}
                    style={{ width: `${Math.min(100, t.avg_score)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-3 flex gap-3 text-[10px] text-slate-400">
          <span className="inline-flex items-center gap-1">
            <i className="w-2 h-2 rounded-full bg-emerald-400" /> сильно
          </span>
          <span className="inline-flex items-center gap-1">
            <i className="w-2 h-2 rounded-full bg-amber-400" /> ок
          </span>
          <span className="inline-flex items-center gap-1">
            <i className="w-2 h-2 rounded-full bg-rose-400" /> слабо
          </span>
        </div>
      </PortalCard>

      <PortalCard className="p-5">
        <h3 className="font-semibold text-slate-800 mb-3">Динамика AI</h3>
        {data.recent_scores.length === 0 ? (
          <p className="text-sm text-slate-500">Сдайте ДЗ с фото — здесь появятся оценки</p>
        ) : (
          <ul className="space-y-2">
            {data.recent_scores.map((s) => (
              <li
                key={`${s.homework_id}-${s.date}`}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="text-slate-600">{s.date ? formatRuDate(s.date) : "—"}</span>
                <span className="font-semibold text-brand-blue">{s.score}%</span>
              </li>
            ))}
          </ul>
        )}
      </PortalCard>
    </>
  );
}
