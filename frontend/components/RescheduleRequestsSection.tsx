"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { formatLessonTime } from "@/lib/calendar";
import Alert from "@/components/Alert";

type Item = Awaited<ReturnType<typeof api.reschedule.list>>[number];

export default function RescheduleRequestsSection() {
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(() => {
    api.reschedule
      .list("pending")
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resolve = async (id: number, status: "approved" | "rejected") => {
    setBusyId(id);
    setError("");
    try {
      await api.reschedule.resolve(id, { status });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setBusyId(null);
    }
  };

  if (items.length === 0) return null;

  return (
    <section className="mt-8 p-6 rounded-2xl bg-white border shadow-sm">
      <h2 className="font-semibold text-brand-blue text-lg">Запросы на перенос</h2>
      <p className="text-sm text-slate-500 mt-1">Ученики просят сдвинуть урок</p>
      {error && (
        <div className="mt-3">
          <Alert message={error} onClose={() => setError("")} />
        </div>
      )}
      <ul className="mt-4 space-y-3">
        {items.map((r) => (
          <li key={r.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50/80">
            <div className="flex flex-wrap justify-between gap-2">
              <div>
                <p className="font-medium text-slate-900">{r.student_name}</p>
                <p className="text-sm text-slate-600 mt-0.5">
                  {new Date(r.lesson_date).toLocaleDateString("ru-RU")} ·{" "}
                  {formatLessonTime(r.lesson_time)}
                </p>
                {r.message && <p className="text-sm text-slate-700 mt-2">{r.message}</p>}
                {(r.preferred_date || r.preferred_time) && (
                  <p className="text-xs text-slate-500 mt-1">
                    Желает:{" "}
                    {r.preferred_date
                      ? new Date(r.preferred_date).toLocaleDateString("ru-RU")
                      : "—"}
                    {r.preferred_time ? ` · ${formatLessonTime(r.preferred_time)}` : ""}
                  </p>
                )}
              </div>
              <Link href={`/lessons/${r.lesson_id}`} className="text-sm text-brand-blue hover:underline">
                Урок →
              </Link>
            </div>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                disabled={busyId === r.id}
                onClick={() => resolve(r.id, "approved")}
                className="px-3 py-2 rounded-xl bg-brand-green text-white text-sm font-medium disabled:opacity-50"
              >
                Согласовать
              </button>
              <button
                type="button"
                disabled={busyId === r.id}
                onClick={() => resolve(r.id, "rejected")}
                className="px-3 py-2 rounded-xl border border-slate-200 text-sm font-medium disabled:opacity-50"
              >
                Отклонить
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
