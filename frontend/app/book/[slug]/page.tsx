"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function BookTrialPage() {
  const params = useParams();
  const slug = String(params.slug || "");

  const [page, setPage] = useState<Awaited<ReturnType<typeof api.booking.getPublic>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [childName, setChildName] = useState("");
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");
  const [parentName, setParentName] = useState("");
  const [parentEmail, setParentEmail] = useState("");
  const [parentPhone, setParentPhone] = useState("");
  const [slotKey, setSlotKey] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!slug) return;
    api.booking
      .getPublic(slug)
      .then((data) => {
        setPage(data);
        if (data.grade_levels.length === 1) setGrade(data.grade_levels[0]);
        if (data.subjects.length === 1) setSubject(data.subjects[0]);
        if (data.slots.length === 1) {
          setSlotKey(`${data.slots[0].date}|${data.slots[0].time}`);
        }
      })
      .catch(() => setPage(null))
      .finally(() => setLoading(false));
  }, [slug]);

  const selectedSlot = page?.slots.find((s) => `${s.date}|${s.time}` === slotKey);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSlot) {
      setError("Выберите удобное время");
      return;
    }
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      const res = await api.booking.submit(slug, {
        child_name: childName,
        grade,
        subject,
        parent_name: parentName,
        parent_email: parentEmail,
        parent_phone: parentPhone,
        preferred_date: selectedSlot.date,
        preferred_time: selectedSlot.time,
        message,
      });
      setSuccess(res.message);
      setChildName("");
      setParentName("");
      setParentEmail("");
      setParentPhone("");
      setMessage("");
      setSlotKey("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось отправить заявку");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner label="Загрузка..." />;

  if (!page) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-slate-50">
        <div className="max-w-md text-center space-y-4">
          <h1 className="text-2xl font-bold text-brand-blue">Запись на пробный урок</h1>
          <Alert message="Страница не найдена или запись отключена" />
        </div>
      </div>
    );
  }

  const gradeOptions =
    page.grade_levels.length > 0 ? page.grade_levels : ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"];
  const subjectOptions = page.subjects.length > 0 ? page.subjects : ["Предмет"];

  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-lg mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-brand-blue">Пробный урок</h1>
          <p className="text-slate-600 mt-2">
            Репетитор: <strong>{page.tutor_name}</strong>
          </p>
          {page.teaching_format && (
            <p className="text-sm text-slate-500 mt-1">Формат: {page.teaching_format}</p>
          )}
        </div>

        {error && (
          <div className="mb-4">
            <Alert message={error} onClose={() => setError("")} />
          </div>
        )}
        {success && (
          <div className="mb-4">
            <Alert type="success" message={success} />
          </div>
        )}

        <form
          onSubmit={submit}
          className="bg-white rounded-2xl border shadow-sm p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium mb-1">Имя ребёнка</label>
            <input
              required
              value={childName}
              onChange={(e) => setChildName(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Класс</label>
              <select
                required
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border"
              >
                <option value="">—</option>
                {gradeOptions.map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Предмет</label>
              <select
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border"
              >
                <option value="">—</option>
                {subjectOptions.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Имя родителя</label>
            <input
              required
              value={parentName}
              onChange={(e) => setParentName(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email родителя</label>
            <input
              type="email"
              required
              value={parentEmail}
              onChange={(e) => setParentEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Телефон (необязательно)</label>
            <input
              type="tel"
              value={parentPhone}
              onChange={(e) => setParentPhone(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Удобное время</label>
            {page.slots.length === 0 ? (
              <p className="text-sm text-amber-600">Свободных слотов пока нет — свяжитесь с репетитором напрямую</p>
            ) : (
              <select
                required
                value={slotKey}
                onChange={(e) => setSlotKey(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border"
              >
                <option value="">Выберите слот</option>
                {page.slots.map((s) => (
                  <option key={`${s.date}|${s.time}`} value={`${s.date}|${s.time}`}>
                    {s.label}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Комментарий (необязательно)</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 rounded-xl border"
              placeholder="Пожелания по формату, цели занятий…"
            />
          </div>

          <button
            type="submit"
            disabled={submitting || page.slots.length === 0}
            className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold disabled:opacity-50"
          >
            {submitting ? "Отправка…" : "Записаться на пробный"}
          </button>
        </form>

        <p className="text-center text-xs text-slate-400 mt-6">
          Powered by{" "}
          <Link href="/" className="text-brand-blue hover:underline">
            RepetCRM
          </Link>
        </p>
      </div>
    </div>
  );
}
