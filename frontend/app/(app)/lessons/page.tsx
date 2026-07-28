"use client";

import { useCallback, useEffect, useState } from "react";
import {
  PlusIcon,
  CalendarDaysIcon,
  TableCellsIcon,
  PencilIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline";
import { api, LessonListItem } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import LessonsCalendar, { CalendarLesson } from "@/components/LessonsCalendar";
import LessonFormModal, { LessonFormData } from "@/components/LessonFormModal";
import { toDateKey, formatLessonTime, formatMonthYear, monthDateRange } from "@/lib/calendar";
import { formatMoney } from "@/lib/currency";

type Lesson = CalendarLesson & {
  student_id: number;
  board_id?: number | null;
  payment_amount: number;
  notes?: string;
  meeting_url?: string;
};

function toCalendarLesson(item: LessonListItem): Lesson {
  return {
    id: item.id,
    student_id: item.student_id,
    board_id: item.board_id ?? null,
    lesson_date: item.lesson_date,
    lesson_time: item.lesson_time,
    student_name: item.student_name,
    duration_minutes: item.duration_minutes,
    is_paid: item.is_paid,
    payment_amount: item.payment_amount,
    notes: item.notes || "",
    meeting_url: item.meeting_url || "",
    homework: item.homework_id ? { id: item.homework_id } : null,
  };
}

export default function LessonsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [students, setStudents] = useState<{ id: number; name: string }[]>([]);
  const [filters, setFilters] = useState({
    student_id: "",
    is_paid: "",
    is_conducted: "",
    status: "",
  });
  const [cursor, setCursor] = useState(() => {
    const n = new Date();
    return { year: n.getFullYear(), month: n.getMonth() };
  });
  const [createDate, setCreateDate] = useState<string | null>(null);
  const [editLesson, setEditLesson] = useState<LessonFormData | null>(null);

  const loadLessons = useCallback(() => {
    const { from, to } = monthDateRange(cursor.year, cursor.month);
    setLoading(true);
    const params: Parameters<typeof api.lessons.list>[0] = { from, to };
    if (filters.student_id) params.student_id = Number(filters.student_id);
    if (filters.is_paid === "paid") params.is_paid = true;
    if (filters.is_paid === "unpaid") params.is_paid = false;
    if (filters.is_conducted === "yes") params.is_conducted = true;
    if (filters.is_conducted === "no") params.is_conducted = false;
    if (filters.status) params.status = filters.status;
    api.lessons
      .list(params)
      .then((items) => setLessons(items.map(toCalendarLesson)))
      .finally(() => setLoading(false));
  }, [cursor, filters]);

  useEffect(() => {
    api.students.listAll().then(setStudents);
  }, []);

  useEffect(() => {
    loadLessons();
  }, [loadLessons]);

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
      meeting_url: full.meeting_url || "",
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

  const monthNav = (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <button
        type="button"
        onClick={prevMonth}
        className="p-2 rounded-lg hover:bg-slate-100 border border-slate-200"
        aria-label="Предыдущий месяц"
      >
        <ChevronLeftIcon className="w-5 h-5 text-slate-600" />
      </button>
      <h2 className="text-lg font-bold text-brand-blue min-w-[180px] text-center">
        {formatMonthYear(cursor.year, cursor.month)}
      </h2>
      <button
        type="button"
        onClick={nextMonth}
        className="p-2 rounded-lg hover:bg-slate-100 border border-slate-200"
        aria-label="Следующий месяц"
      >
        <ChevronRightIcon className="w-5 h-5 text-slate-600" />
      </button>
      <button
        type="button"
        onClick={goToday}
        className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 hover:bg-slate-50"
      >
        Сегодня
      </button>
    </div>
  );

  if (loading && lessons.length === 0) return <LoadingSpinner />;

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="rc-page-title">Занятия</h1>
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

      <div className="mt-6 flex flex-wrap gap-3 p-4 rounded-2xl bg-white border border-slate-100">
        <select
          value={filters.student_id}
          onChange={(e) => setFilters((f) => ({ ...f, student_id: e.target.value }))}
          className="px-3 py-2 rounded-xl border text-sm"
        >
          <option value="">Все ученики</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          value={filters.is_paid}
          onChange={(e) => setFilters((f) => ({ ...f, is_paid: e.target.value }))}
          className="px-3 py-2 rounded-xl border text-sm"
        >
          <option value="">Оплата: все</option>
          <option value="paid">Оплачено</option>
          <option value="unpaid">Не оплачено</option>
        </select>
        <select
          value={filters.is_conducted}
          onChange={(e) => setFilters((f) => ({ ...f, is_conducted: e.target.value }))}
          className="px-3 py-2 rounded-xl border text-sm"
        >
          <option value="">Проведение: все</option>
          <option value="yes">Проведено</option>
          <option value="no">Не проведено</option>
        </select>
        <select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="px-3 py-2 rounded-xl border text-sm"
        >
          <option value="">Статус: все</option>
          <option value="scheduled">Запланировано</option>
          <option value="completed">Завершено</option>
          <option value="cancelled">Отменено</option>
          <option value="no_show">Неявка</option>
          <option value="rescheduled">Перенесено</option>
        </select>
        {(filters.student_id || filters.is_paid || filters.is_conducted || filters.status) && (
          <button
            type="button"
            onClick={() =>
              setFilters({ student_id: "", is_paid: "", is_conducted: "", status: "" })
            }
            className="px-3 py-2 text-sm text-brand-blue hover:underline"
          >
            Сбросить
          </button>
        )}
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
        <div className="mt-8">
          {monthNav}
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {lessons.map((l) => (
              <div
                key={l.id}
                className="p-4 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-3"
              >
                <div className="flex justify-between items-start gap-2">
                  <div>
                    <p className="font-semibold text-brand-blue">{l.student_name}</p>
                    <p className="text-sm text-slate-600 mt-0.5">
                      {new Date(l.lesson_date).toLocaleDateString("ru-RU")} ·{" "}
                      {formatLessonTime(l.lesson_time)}
                    </p>
                  </div>
                  <span className="text-xs text-slate-500">{l.duration_minutes} мин</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={async () => {
                      await api.lessons.togglePaid(l.id, !l.is_paid);
                      loadLessons();
                    }}
                    className={`flex-1 min-w-[120px] py-2 rounded-xl text-sm font-medium border ${
                      l.is_paid
                        ? "border-brand-green text-brand-green bg-emerald-50"
                        : "border-amber-300 text-amber-700 bg-amber-50"
                    }`}
                  >
                    {l.is_paid ? `✓ ${formatMoney(l.payment_amount)}` : "Не оплачено"}
                  </button>
                  {l.board_id ? (
                    <a
                      href={`/boards/${l.board_id}?lesson=${l.id}`}
                      className="px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-medium"
                    >
                      Доска
                    </a>
                  ) : null}
                  <a
                    href={`/lessons/${l.id}`}
                    className="px-4 py-2 rounded-xl border text-sm font-medium text-brand-blue"
                  >
                    Урок
                  </a>
                </div>
              </div>
            ))}
            {lessons.length === 0 && (
              <p className="p-8 text-center text-slate-500 rounded-2xl bg-white border">
                Нет занятий в этом месяце
              </p>
            )}
          </div>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto rounded-2xl bg-white border border-slate-100 shadow-sm">
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
              <p className="p-8 text-center text-slate-500">Нет занятий в этом месяце</p>
            )}
          </div>
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
