"use client";

import {
  ChevronLeftIcon,
  ChevronRightIcon,
  PlusIcon,
  PencilSquareIcon,
} from "@heroicons/react/24/outline";
import {
  buildMonthGrid,
  formatMonthYear,
  formatLessonTime,
  compareLessonTime,
  WEEKDAYS,
} from "@/lib/calendar";

export type CalendarLesson = {
  id: number;
  lesson_date: string;
  lesson_time?: string;
  student_name?: string;
  duration_minutes: number;
  is_paid: boolean;
  homework?: { id: number } | null;
  board_id?: number | null;
};

export default function LessonsCalendar({
  lessons,
  year,
  month,
  onPrevMonth,
  onNextMonth,
  onToday,
  onAddLesson,
  onDayClick,
  onLessonClick,
}: {
  lessons: CalendarLesson[];
  year: number;
  month: number;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  onToday: () => void;
  onAddLesson: (dateKey: string) => void;
  onDayClick?: (dateKey: string) => void;
  onLessonClick?: (lesson: CalendarLesson) => void;
}) {
  const cells = buildMonthGrid(year, month);
  const byDate = lessons.reduce<Record<string, CalendarLesson[]>>((acc, l) => {
    const key = l.lesson_date.slice(0, 10);
    if (!acc[key]) acc[key] = [];
    acc[key].push(l);
    return acc;
  }, {});
  Object.keys(byDate).forEach((key) => {
    byDate[key].sort((a, b) =>
      compareLessonTime(a.lesson_time || "00:00", b.lesson_time || "00:00")
    );
  });

  return (
    <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 px-4 py-4 border-b border-slate-100 bg-slate-50/80">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onPrevMonth}
            className="p-2 rounded-lg hover:bg-white border border-transparent hover:border-slate-200"
            aria-label="Предыдущий месяц"
          >
            <ChevronLeftIcon className="w-5 h-5 text-slate-600" />
          </button>
          <h2 className="text-lg font-bold text-brand-blue min-w-[180px] text-center">
            {formatMonthYear(year, month)}
          </h2>
          <button
            type="button"
            onClick={onNextMonth}
            className="p-2 rounded-lg hover:bg-white border border-transparent hover:border-slate-200"
            aria-label="Следующий месяц"
          >
            <ChevronRightIcon className="w-5 h-5 text-slate-600" />
          </button>
        </div>
        <button
          type="button"
          onClick={onToday}
          className="text-sm font-medium text-brand-blue hover:underline"
        >
          Сегодня
        </button>
      </div>

      <div className="grid grid-cols-7 border-b border-slate-100 bg-slate-50">
        {WEEKDAYS.map((d) => (
          <div
            key={d}
            className="py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide"
          >
            {d}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 auto-rows-fr min-h-[480px] lg:min-h-[560px]">
        {cells.map((cell) => {
          const dayLessons = byDate[cell.dateKey] || [];
          return (
            <div
              key={cell.dateKey}
              className={`group min-h-[80px] lg:min-h-[96px] border-b border-r border-slate-100 p-1.5 flex flex-col ${
                cell.inMonth ? "bg-white" : "bg-slate-50/60"
              } ${cell.isToday ? "ring-2 ring-inset ring-brand-green/50" : ""}`}
            >
              <div className="flex items-center justify-between gap-1 mb-1">
                <button
                  type="button"
                  onClick={() => onDayClick?.(cell.dateKey)}
                  className={`text-sm font-medium w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                    cell.isToday
                      ? "bg-brand-green text-white"
                      : cell.inMonth
                        ? "text-slate-700 hover:bg-slate-100"
                        : "text-slate-400"
                  }`}
                >
                  {cell.date.getDate()}
                </button>
                {cell.inMonth && (
                  <button
                    type="button"
                    onClick={() => onAddLesson(cell.dateKey)}
                    className="p-1 rounded-md text-slate-400 hover:text-brand-green hover:bg-emerald-50 transition"
                    title="Добавить занятие"
                    aria-label={`Добавить занятие ${cell.dateKey}`}
                  >
                    <PlusIcon className="w-4 h-4" />
                  </button>
                )}
              </div>
              <div className="flex-1 space-y-1 overflow-y-auto max-h-[72px] lg:max-h-[88px] group">
                {dayLessons.map((l) => (
                  <div
                    key={l.id}
                    className={`w-full rounded-md text-xs border transition ${
                      l.is_paid
                        ? "bg-emerald-50 border-emerald-100 text-emerald-900"
                        : "bg-amber-50 border-amber-100 text-amber-900"
                    }`}
                    title={`${formatLessonTime(l.lesson_time)} ${l.student_name} · ${l.duration_minutes} мин`}
                  >
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => onLessonClick?.(l)}
                        className={`flex-1 text-left px-1.5 py-1 rounded-md hover:opacity-90`}
                      >
                        <span className="font-semibold text-[10px] opacity-80">
                          {formatLessonTime(l.lesson_time)}
                        </span>{" "}
                        <span className="font-medium">{l.student_name}</span>
                        {l.homework && (
                          <span className="ml-1 text-[10px] text-brand-green">ДЗ</span>
                        )}
                      </button>
                      {l.board_id ? (
                        <a
                          href={`/boards/${l.board_id}?lesson=${l.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="shrink-0 mr-1.5 p-1 rounded-md bg-white/60 hover:bg-white/90 border border-slate-200/60"
                          title="Открыть доску"
                        >
                          <PencilSquareIcon className="w-4 h-4 text-slate-700" />
                        </a>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="px-4 py-3 flex flex-wrap gap-4 text-xs text-slate-500 border-t border-slate-100 bg-slate-50/50">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-emerald-100 border border-emerald-200" />
          Оплачено
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-amber-100 border border-amber-200" />
          Не оплачено
        </span>
        <span>Клик по занятию — редактирование · «+» — новое на этот день</span>
      </div>
    </div>
  );
}
