"use client";

import { useEffect, useState } from "react";
import {
  PlusIcon,
  CalendarDaysIcon,
  TableCellsIcon,
  PencilIcon,
} from "@heroicons/react/24/outline";
import { getToken } from "@/lib/auth";
import { api } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import LessonsCalendar, { CalendarLesson } from "@/components/LessonsCalendar";
import LessonFormModal, { LessonFormData } from "@/components/LessonFormModal";
import { toDateKey, formatLessonTime } from "@/lib/calendar";
import { formatMoney } from "@/lib/currency";

type Lesson = CalendarLesson & {
  student_id: number;
  board_id?: number | null;
  payment_amount: number;
  notes?: string;
};

export default function LessonsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [cursor, setCursor] = useState(() => {
    const n = new Date();
    return { year: n.getFullYear(), month: n.getMonth() };
  });
  const [createDate, setCreateDate] = useState<string | null>(null);
  const [editLesson, setEditLesson] = useState<LessonFormData | null>(null);

  const loadLessons = () => {
    const token = getToken();
    if (!token) return;
    api.lessons.list<Lesson[]>(token).then(setLessons);
  };

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.lessons.list<Lesson[]>(token).then(setLessons).finally(() => setLoading(false));
  }, []);

  const openCreate = (dateKey: string) => {
    setEditLesson(null);
    setCreateDate(dateKey);
  };

  const openEdit = (l: CalendarLesson) => {
    const full = lessons.find((x) => x.id === l.id);
    if (!full) return;
    setCreateDate(null);
    setEditLesson({
      id: full.id,
      student_id: full.student_id,
      student_name: full.student_name,
      board_id: full.board_id ?? null,
      lesson_date: full.lesson_date.slice(0, 10),
      lesson_time: full.lesson_time || "10:00",
      duration_minutes: full.duration_minutes,
      payment_amount: full.payment_amount,
      is_paid: full.is_paid,
      notes: full.notes || "",
    });
  };

  const prevMonth = () => {
    setCursor((c) => {
      if (c.month === 0) return { year: c.year - 1, month: 11 };
      return { ...c, month: c.month - 1 };
    });
  };

  const nextMonth = () => {
    setCursor((c) => {
      if (c.month === 11) return { year: c.year + 1, month: 0 };
      return { ...c, month: c.month + 1 };
    });
  };

  const goToday = () => {
    const n = new Date();
    setCursor({ year: n.getFullYear(), month: n.getMonth() });
  };

  if (loading && lessons.length === 0) return <LoadingSpinner />;

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-brand-blue">Занятия</h1>
          <p className="text-slate-500 text-sm mt-1">Календарь с временем · редактирование и оплата</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex rounded-lg border border-slate-200 p-0.5 bg-white text-sm">
            <button
              type="button"
              onClick={() => setView("calendar")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md ${
                view === "calendar" ? "bg-brand-blue text-white" : "text-slate-600"
              }`}
            >
              <CalendarDaysIcon className="w-4 h-4" />
              Календарь
            </button>
            <button
              type="button"
              onClick={() => setView("list")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md ${
                view === "list" ? "bg-brand-blue text-white" : "text-slate-600"
              }`}
            >
              <TableCellsIcon className="w-4 h-4" />
              Список
            </button>
          </div>
          <button
            type="button"
            onClick={() => openCreate(toDateKey(new Date()))}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-green text-white font-medium hover:bg-emerald-600"
          >
            <PlusIcon className="w-5 h-5" />
            Новое занятие
          </button>
        </div>
      </div>

      {view === "calendar" ? (
        <div className="mt-8">
          <LessonsCalendar
            lessons={lessons}
            year={cursor.year}
            month={cursor.month}
            onPrevMonth={prevMonth}
            onNextMonth={nextMonth}
            onToday={goToday}
            onAddLesson={openCreate}
            onDayClick={openCreate}
            onLessonClick={openEdit}
          />
        </div>
      ) : (
        <div className="mt-8 overflow-x-auto rounded-2xl bg-white border border-slate-100 shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Дата</th>
                <th className="px-4 py-3 font-medium">Время</th>
                <th className="px-4 py-3 font-medium">Ученик</th>
                <th className="px-4 py-3 font-medium">Длительность</th>
                <th className="px-4 py-3 font-medium">Оплата</th>
                <th className="px-4 py-3 font-medium">ДЗ</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {lessons.map((l) => (
                <tr key={l.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    {new Date(l.lesson_date).toLocaleDateString("ru-RU")}
                  </td>
                  <td className="px-4 py-3 font-medium">{formatLessonTime(l.lesson_time)}</td>
                  <td className="px-4 py-3 font-medium">{l.student_name}</td>
                  <td className="px-4 py-3">{l.duration_minutes} мин</td>
                  <td className="px-4 py-3">
                    {l.is_paid ? (
                      <span className="text-brand-green">{formatMoney(l.payment_amount)}</span>
                    ) : (
                      <span className="text-amber-600">Не оплачено</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {l.homework ? (
                      <span className="text-brand-green">✓</span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => openEdit(l)}
                      className="inline-flex items-center gap-1 text-brand-blue hover:underline"
                    >
                      <PencilIcon className="w-4 h-4" />
                      Изменить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {lessons.length === 0 && (
            <p className="p-8 text-center text-slate-500">Нажмите «+» в календаре или создайте занятие</p>
          )}
        </div>
      )}

      {createDate && (
        <LessonFormModal
          mode="create"
          initialDate={createDate}
          onClose={() => setCreateDate(null)}
          onSaved={() => {
            setCreateDate(null);
            loadLessons();
          }}
        />
      )}

      {editLesson && (
        <LessonFormModal
          mode="edit"
          lesson={editLesson}
          onClose={() => setEditLesson(null)}
          onSaved={() => {
            setEditLesson(null);
            loadLessons();
          }}
        />
      )}
    </div>
  );
}
