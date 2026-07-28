"use client";

import { formatRuDate } from "@/lib/portalUi";
import { PortalCard, PortalEmpty } from "./PortalShell";

type Progress = {
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
};

export default function PortalProgress({ data }: { data: Progress | null }) {
  if (!data) {
    return <PortalEmpty title="Загружаем прогресс…" />;
  }

  const donePct =
    data.homework_total > 0
      ? Math.round((data.homework_submitted / data.homework_total) * 100)
      : 0;

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        <PortalCard className="p-4">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">Сдано ДЗ</p>
          <p className="text-2xl font-bold text-brand-blue mt-1">
            {data.homework_submitted}
            <span className="text-base font-medium text-slate-400">/{data.homework_total}</span>
          </p>
          <div className="mt-2 h-1.5 rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full bg-brand-green rounded-full" style={{ width: `${donePct}%` }} />
          </div>
        </PortalCard>
        <PortalCard className="p-4">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">Серия дней</p>
          <p className="text-2xl font-bold text-brand-blue mt-1">{data.streak_days}</p>
          <p className="text-xs text-slate-500 mt-1">дней подряд со сдачей</p>
        </PortalCard>
        <PortalCard className="p-4">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">Средняя AI</p>
          <p className="text-2xl font-bold text-brand-blue mt-1">
            {data.avg_ai_score != null ? `${Math.round(data.avg_ai_score)}%` : "—"}
          </p>
          <p className="text-xs text-slate-500 mt-1">по проверенным работам</p>
        </PortalCard>
        <PortalCard className="p-4">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">Проверено</p>
          <p className="text-2xl font-bold text-brand-blue mt-1">{data.homework_reviewed}</p>
          {data.homework_needs_revision > 0 && (
            <p className="text-xs text-amber-700 mt-1">доработать: {data.homework_needs_revision}</p>
          )}
        </PortalCard>
      </div>

      <PortalCard className="p-5">
        <h3 className="font-semibold text-slate-800 mb-3">Темы уроков</h3>
        {data.topics.length === 0 ? (
          <p className="text-sm text-slate-500">Темы появятся после проведённых занятий</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {data.topics.map((t) => (
              <span
                key={t}
                className="text-xs font-medium px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </PortalCard>

      <PortalCard className="p-5">
        <h3 className="font-semibold text-slate-800 mb-3">Динамика оценок AI</h3>
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
