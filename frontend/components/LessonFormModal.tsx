"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { XMarkIcon, TrashIcon } from "@heroicons/react/24/outline";
import { getToken } from "@/lib/auth";
import { api, ApiError, LessonWithBoundarySync, BoundarySyncOut } from "@/lib/api";
import Alert from "@/components/Alert";
import { formatDayLabel } from "@/lib/calendar";
import { CURRENCY_SYMBOL } from "@/lib/currency";
import { toast } from "@/lib/toast";
import { ClipboardDocumentIcon } from "@heroicons/react/24/outline";

type StudentOption = { id: number; name: string; subject?: string; grade?: string };

export type LessonFormData = {
  id?: number;
  student_id: number;
  student_name?: string;
  board_id?: number | null;
  lesson_date: string;
  lesson_time: string;
  duration_minutes: number;
  payment_amount: number;
  is_paid: boolean;
  notes: string;
};

export default function LessonFormModal({
  mode,
  initialDate,
  lesson,
  onClose,
  onSaved,
}: {
  mode: "create" | "edit";
  initialDate?: string;
  lesson?: LessonFormData;
  onClose: () => void;
  onSaved?: () => void;
}) {
  const router = useRouter();
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [loadingStudents, setLoadingStudents] = useState(mode === "create");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [boundarySync, setBoundarySync] = useState<BoundarySyncOut | null>(null);
  const [copying, setCopying] = useState(false);

  const [form, setForm] = useState({
    student_id: lesson ? String(lesson.student_id) : "",
    lesson_date: lesson?.lesson_date || initialDate || new Date().toISOString().slice(0, 10),
    lesson_time: lesson?.lesson_time?.slice(0, 5) || "10:00",
    duration_minutes: lesson?.duration_minutes ?? 60,
    payment_amount: lesson?.payment_amount ?? 0,
    is_paid: lesson?.is_paid ?? false,
    notes: lesson?.notes ?? "",
  });

  useEffect(() => {
    if (mode === "create" && initialDate) {
      setForm((f) => ({ ...f, lesson_date: initialDate }));
    }
  }, [initialDate, mode]);

  useEffect(() => {
    if (mode === "create") {
      const token = getToken();
      if (!token) return;
      api.students
        .listAll(token)
        .then((list) => {
          setStudents(list);
          if (list.length) setForm((f) => ({ ...f, student_id: String(list[0].id) }));
        })
        .finally(() => setLoadingStudents(false));
    }
  }, [mode]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    setSaving(true);
    setError("");
    setBoundarySync(null);
    try {
      if (mode === "create") {
        const created = await api.lessons.create<{ id: number }>(token, {
          student_id: Number(form.student_id),
          lesson_date: form.lesson_date,
          lesson_time: form.lesson_time,
          duration_minutes: Number(form.duration_minutes),
          payment_amount: Number(form.payment_amount),
          is_paid: form.is_paid,
          notes: form.notes,
        });
        if (onSaved) onSaved();
        else router.push(`/lessons/${created.id}`);
      } else if (lesson?.id) {
        const res = await api.lessons.update<LessonWithBoundarySync<unknown>>(token, lesson.id, {
          lesson_date: form.lesson_date,
          lesson_time: form.lesson_time,
          duration_minutes: Number(form.duration_minutes),
          payment_amount: Number(form.payment_amount),
          is_paid: form.is_paid,
          notes: form.notes,
        });
        const sync = res?.boundary_sync ?? null;
        setBoundarySync(sync);
        if (sync?.mode_changed) {
          const title = sync.escalated
            ? `Границы ужесточены: ${sync.previous_mode} → ${sync.new_mode}`
            : `Границы обновлены: ${sync.previous_mode} → ${sync.new_mode}`;
          toast(title, sync.escalated ? "info" : "success");
          if (sync.message) {
            try {
              await navigator.clipboard.writeText(sync.message);
              toast("Сообщение скопировано — вставь ученику/родителю", "success");
            } catch {
              toast("Не удалось скопировать сообщение автоматически", "error");
            }
          }
        }
        onSaved?.();
        // Keep modal open if we have a message to show.
        if (!sync?.message) onClose();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!lesson?.id) return;
    if (!confirm("Удалить занятие? Чек-лист и домашка тоже будут удалены.")) return;
    const token = getToken();
    if (!token) return;
    setDeleting(true);
    try {
      await api.lessons.delete(token, lesson.id);
      onSaved?.();
      onClose();
      router.push("/lessons");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка удаления");
    } finally {
      setDeleting(false);
    }
  };

  const title = mode === "create" ? "Новое занятие" : "Редактировать занятие";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl my-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div>
            <h2 className="font-bold text-lg text-brand-blue">{title}</h2>
            <p className="text-sm text-slate-500">{formatDayLabel(form.lesson_date)}</p>
            {mode === "edit" && lesson?.student_name && (
              <p className="text-sm font-medium text-brand-blue mt-0.5">{lesson.student_name}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-500"
            aria-label="Закрыть"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {loadingStudents ? (
          <div className="p-8 flex justify-center">
            <div className="animate-spin w-8 h-8 border-4 border-brand-blue border-t-transparent rounded-full" />
          </div>
        ) : mode === "create" && students.length === 0 ? (
          <div className="p-6 text-sm text-slate-600">
            <p>Сначала добавьте ученика.</p>
            <Link href="/students" className="mt-3 inline-block text-brand-blue font-medium hover:underline">
              Перейти к ученикам →
            </Link>
          </div>
        ) : (
          <form onSubmit={submit} className="p-6 space-y-4">
            {error && <Alert message={error} onClose={() => setError("")} />}
            {boundarySync?.message && (
              <Alert
                type="info"
                message={`CRM сгенерировала сообщение для границ (${boundarySync.new_mode}). Оно уже в буфере обмена.`}
                onClose={() => setBoundarySync(null)}
              />
            )}
            {boundarySync?.message && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                      Сообщение для ученика/родителя
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Если автокопирование не сработало — нажми кнопку или скопируй вручную.
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={copying}
                    onClick={async () => {
                      if (!boundarySync?.message) return;
                      setCopying(true);
                      try {
                        await navigator.clipboard.writeText(boundarySync.message);
                        toast("Сообщение скопировано", "success");
                      } catch {
                        toast("Не удалось скопировать — выдели и скопируй вручную", "error");
                      } finally {
                        setCopying(false);
                      }
                    }}
                    className="shrink-0 inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    title="Скопировать сообщение"
                  >
                    <ClipboardDocumentIcon className="w-4 h-4" />
                    {copying ? "Копирую…" : "Скопировать ещё раз"}
                  </button>
                </div>
                <textarea
                  readOnly
                  value={boundarySync.message}
                  className="w-full h-28 px-3 py-2 rounded-xl border border-slate-200 bg-white text-sm text-slate-800"
                />
              </div>
            )}

            {mode === "create" && (
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Ученик *</label>
                <select
                  value={form.student_id}
                  onChange={(e) => setForm({ ...form, student_id: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200"
                  required
                >
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                      {s.grade ? ` · ${s.grade}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Дата *</label>
                <input
                  type="date"
                  value={form.lesson_date}
                  onChange={(e) => setForm({ ...form, lesson_date: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Время *</label>
                <input
                  type="time"
                  value={form.lesson_time}
                  onChange={(e) => setForm({ ...form, lesson_time: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-slate-200"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">Длительность (мин)</label>
              <input
                type="number"
                min={15}
                step={15}
                value={form.duration_minutes}
                onChange={(e) =>
                  setForm({ ...form, duration_minutes: Number(e.target.value) })
                }
                className="w-full px-4 py-3 rounded-xl border border-slate-200"
              />
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-3">
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Оплата</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Сумма ({CURRENCY_SYMBOL})</label>
                  <input
                    type="number"
                    min={0}
                    value={form.payment_amount}
                    onChange={(e) =>
                      setForm({ ...form, payment_amount: Number(e.target.value) })
                    }
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white"
                  />
                </div>
                <div className="flex items-end pb-3">
                  <label className="flex items-center gap-2 cursor-pointer text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={form.is_paid}
                      onChange={(e) => setForm({ ...form, is_paid: e.target.checked })}
                      className="w-5 h-5 rounded text-brand-green"
                    />
                    <span className={form.is_paid ? "text-brand-green" : "text-amber-600"}>
                      {form.is_paid ? "Оплачено" : "Не оплачено"}
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {mode === "edit" && lesson?.id && (
              <div className="grid grid-cols-2 gap-2">
                <Link
                  href={`/lessons/${lesson.id}`}
                  className="inline-flex items-center justify-center text-sm text-brand-blue hover:underline py-2"
                >
                  Чек-лист и домашка →
                </Link>
                {lesson.board_id ? (
                  <Link
                    href={`/boards/${lesson.board_id}?lesson=${lesson.id}`}
                    className="inline-flex items-center justify-center text-sm text-slate-900 hover:underline py-2"
                  >
                    Доска →
                  </Link>
                ) : (
                  <span className="inline-flex items-center justify-center text-sm text-slate-400 py-2">
                    Доска (нет)
                  </span>
                )}
              </div>
            )}

            <div className="flex flex-col gap-2 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600 disabled:opacity-60"
              >
                {saving ? "Сохранение..." : mode === "create" ? "Создать занятие" : "Сохранить изменения"}
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 py-3 rounded-xl border border-slate-200"
                >
                  Отмена
                </button>
                {mode === "edit" && (
                  <button
                    type="button"
                    onClick={remove}
                    disabled={deleting}
                    className="inline-flex items-center justify-center gap-1 px-4 py-3 rounded-xl border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-60"
                  >
                    <TrashIcon className="w-4 h-4" />
                    {deleting ? "..." : "Удалить"}
                  </button>
                )}
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
