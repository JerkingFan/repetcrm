"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import LoadingSpinner from "@/components/LoadingSpinner";

function BarChart({
  data,
}: {
  data: Array<{ month: string; revenue: number }>;
}) {
  const max = Math.max(...data.map((d) => d.revenue), 1);
  return (
    <div className="flex items-end gap-2 h-40 mt-4">
      {data.map((d) => (
        <div key={d.month} className="flex-1 flex flex-col items-center gap-1 min-w-0">
          <div
            className="w-full bg-brand-blue rounded-t-md min-h-[4px]"
            style={{ height: `${Math.max(4, (d.revenue / max) * 100)}%` }}
            title={formatMoney(d.revenue)}
          />
          <span className="text-[10px] text-slate-400 truncate w-full text-center">
            {d.month.slice(5)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsSection() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.analytics.overview>> | null>(null);

  useEffect(() => {
    api.analytics.overview().then(setData);
  }, []);

  if (!data) return <LoadingSpinner label="Аналитика..." />;

  return (
    <section className="mt-10 space-y-6">
      <h2 className="text-xl font-bold text-brand-blue">Аналитика</h2>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 p-6 rounded-2xl bg-white border shadow-sm">
          <h3 className="font-semibold">Доход по месяцам</h3>
          <p className="text-xs text-slate-400 mt-1">Сумма оплаченных занятий за 12 месяцев</p>
          {data.revenue_by_month.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Пока нет данных</p>
          ) : (
            <BarChart data={data.revenue_by_month} />
          )}
        </div>

        <div className="p-6 rounded-2xl bg-white border shadow-sm space-y-4">
          <div>
            <h3 className="font-semibold">Конверсия пробных</h3>
            <p className="text-xs text-slate-400">
              За {data.trial_conversion.period_days} дн.: 1 урок → 2+ урока
            </p>
            <p className="text-3xl font-bold text-brand-green mt-2">
              {data.trial_conversion.conversion_rate_percent}%
            </p>
            <p className="text-sm text-slate-500 mt-1">
              {data.trial_conversion.students_converted} из{" "}
              {data.trial_conversion.students_with_any_lesson} учеников
            </p>
          </div>
          <div className="pt-4 border-t">
            <h3 className="font-semibold">Отток</h3>
            <p className="text-xs text-slate-400">
              Нет занятий {data.churn.inactive_days_threshold}+ дней
            </p>
            <p className="text-3xl font-bold text-amber-600 mt-2">
              {data.churn.churn_rate_percent}%
            </p>
            <p className="text-sm text-slate-500 mt-1">
              {data.churn.churned_students} ушли · {data.churn.at_risk_students} под угрозой
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
