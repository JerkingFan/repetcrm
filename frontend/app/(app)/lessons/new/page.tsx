"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/auth";
import { CURRENCY_SYMBOL } from "@/lib/currency";
import { api, ApiError } from "@/lib/api";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function NewLessonPage() {
  const router = useRouter();
  const [students, setStudents] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    student_id: "",
    lesson_date: new Date().toISOString().slice(0, 10),
    lesson_time: "10:00",
    duration_minutes: 60,
    payment_amount: 0,
    is_paid: false,
    notes: "",
  });

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.students.listAll(token).then((s) => {
      setStudents(s);
      if (s.length) setForm((f) => ({ ...f, student_id: String(s[0].id) }));
      setLoading(false);
    });
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    try {
      const lesson = await api.lessons.create<{ id: number }>(token, {
        student_id: Number(form.student_id),
        lesson_date: form.lesson_date,
        lesson_time: form.lesson_time,
        duration_minutes: Number(form.duration_minutes),
        payment_amount: Number(form.payment_amount),
        is_paid: form.is_paid,
        notes: form.notes,
      });
      router.push(`/lessons/${lesson.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка");
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-xl">
      <Link href="/lessons" className="text-sm text-brand-blue hover:underline">← Занятия</Link>
      <h1 className="mt-4 text-2xl font-bold text-brand-blue">Новое занятие</h1>
      {error && <div className="mt-4"><Alert message={error} /></div>}
      {students.length === 0 ? (
        <p className="mt-6 text-slate-500">
          Сначала <Link href="/students" className="text-brand-blue underline">добавьте ученика</Link>
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
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
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
          <button type="submit" className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold">
            Создать и заполнить чек-лист →
          </button>
        </form>
      )}
    </div>
  );
}
