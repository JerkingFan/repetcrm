"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { CURRENCY_SYMBOL } from "@/lib/currency";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";

const WEEKDAYS = [
  "Понедельник",
  "Вторник",
  "Среда",
  "Четверг",
  "Пятница",
  "Суббота",
  "Воскресенье",
];

export default function NewLessonPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [students, setStudents] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    student_id: searchParams.get("student_id") || "",
    lesson_date: searchParams.get("date") || new Date().toISOString().slice(0, 10),
    lesson_time: (searchParams.get("time") || "10:00").slice(0, 5),
    duration_minutes: 60,
    payment_amount: 0,
    is_paid: false,
    notes: "",
    meeting_url: "",
    recurring: false,
    weeks_ahead: 8,
    is_trial: searchParams.get("is_trial") === "1",
  });

  useEffect(() => {
    api.students.listAll().then((s) => {
      setStudents(s);
      setForm((f) => {
        if (f.student_id && s.some((x) => String(x.id) === f.student_id)) return f;
        if (s.length) return { ...f, student_id: String(s[0].id) };
        return f;
      });
      setLoading(false);
    });
  }, []);

  const weekdayFromDate = (iso: string) => new Date(iso + "T12:00:00").getDay();
  const jsToIsoWeekday = (js: number) => (js + 6) % 7;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: Record<string, unknown> = {
        student_id: Number(form.student_id),
        lesson_date: form.lesson_date,
        lesson_time: form.lesson_time,
        duration_minutes: Number(form.duration_minutes),
        payment_amount: Number(form.payment_amount),
        is_paid: form.is_paid,
        notes: form.notes,
        meeting_url: form.meeting_url.trim(),
        is_trial: form.is_trial,
      };
      if (form.recurring && !form.is_trial) {
        payload.recurrence = {
          weekday: jsToIsoWeekday(weekdayFromDate(form.lesson_date)),
          weeks_ahead: Number(form.weeks_ahead),
        };
      }
      const result = await api.lessons.create(payload);
      router.push(`/lessons/${result.lesson.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка");
    }
  };

  if (loading) return <LoadingSpinner />;

  const wd = jsToIsoWeekday(weekdayFromDate(form.lesson_date));

  return (
    <div className="max-w-xl">
      <Link href="/lessons" className="text-sm text-brand-blue hover:underline">
        ← Занятия
      </Link>
      <h1 className="mt-4 rc-page-title">Новое занятие</h1>
      {error && (
        <div className="mt-4">
          <Alert message={error} />
        </div>
      )}
      {students.length === 0 ? (
        <p className="mt-6 text-slate-500">
          Сначала{" "}
          <Link href="/students" className="text-brand-blue underline">
            добавьте ученика
          </Link>
        </p>
      ) : (
        <form onSubmit={submit} className="mt-8 space-y-4 bg-white p-6 rounded-2xl border shadow-sm">
          <div>
            <label className="block text-sm font-medium mb-1">Ученик</label>
            <select
              value={form.student_id}
              onChange={(e) => setForm({ ...form, student_id: e.target.value })}
              className="w-full px-4 py-3 rounded-xl border"
              required
            >
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-start gap-3 p-3 rounded-xl border border-teal-100 bg-teal-50/60 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_trial}
              onChange={(e) =>
                setForm({
                  ...form,
                  is_trial: e.target.checked,
                  recurring: e.target.checked ? false : form.recurring,
                })
              }
              className="mt-0.5 w-4 h-4 rounded"
            />
            <span>
              <span className="block text-sm font-medium text-brand-ink">Пробный урок</span>
              <span className="block text-xs text-slate-500 mt-0.5">
                Для офлайн/телефонных заявок: ученик попадёт в воронку пробных
              </span>
            </span>
          </label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Дата</label>
              <input
                type="date"
                value={form.lesson_date}
                onChange={(e) => setForm({ ...form, lesson_date: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Время</label>
              <input
                type="time"
                value={form.lesson_time}
                onChange={(e) => setForm({ ...form, lesson_time: e.target.value })}
                className="w-full px-4 py-3 rounded-xl border"
                required
              />
            </div>
          </div>
          {!form.is_trial && (
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.recurring}
                  onChange={(e) => setForm({ ...form, recurring: e.target.checked })}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm font-medium">Повторять каждую неделю</span>
              </label>
              {form.recurring && (
                <>
                  <p className="text-sm text-slate-600">
                    Каждый <strong>{WEEKDAYS[wd]}</strong> в {form.lesson_time}
                  </p>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Создать занятий вперёд (недель)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={52}
                      value={form.weeks_ahead}
                      onChange={(e) => setForm({ ...form, weeks_ahead: Number(e.target.value) })}
                      className="w-full px-4 py-3 rounded-xl border bg-white"
                    />
                  </div>
                </>
              )}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Длительность (мин)</label>
            <input
              type="number"
              min={15}
              step={15}
              value={form.duration_minutes}
              onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })}
              className="w-full px-4 py-3 rounded-xl border"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Сумма ({CURRENCY_SYMBOL})</label>
              <input
                type="number"
                min={0}
                value={form.payment_amount}
                onChange={(e) => setForm({ ...form, payment_amount: Number(e.target.value) })}
                className="w-full px-4 py-3 rounded-xl border"
              />
            </div>
            <div className="flex items-end pb-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_paid}
                  onChange={(e) => setForm({ ...form, is_paid: e.target.checked })}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm">Оплачено</span>
              </label>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Ссылка на урок</label>
            <input
              type="url"
              value={form.meeting_url}
              onChange={(e) => setForm({ ...form, meeting_url: e.target.value })}
              placeholder="https://zoom.us/… или Meet"
              className="w-full px-4 py-3 rounded-xl border"
            />
          </div>
          <button type="submit" className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold">
            {form.is_trial
              ? "Поставить пробный урок →"
              : form.recurring
                ? "Создать серию занятий →"
                : "Создать и заполнить чек-лист →"}
          </button>
        </form>
      )}
    </div>
  );
}
