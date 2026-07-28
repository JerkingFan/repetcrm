"use client";

import { formatLessonTime } from "@/lib/calendar";
import { formatMoney } from "@/lib/currency";
import {
  formatRuDate,
  formatRuWeekday,
  homeworkDueLabel,
  isToday,
  submissionChipClass,
  SUBMISSION_STATUS_LABEL,
  type PortalTab,
} from "@/lib/portalUi";
import { PortalCard, PortalEmpty } from "./PortalShell";

type Student = {
  name: string;
  subject: string;
  grade: string;
  balance: number;
  show_balance?: boolean;
  tutor_name: string;
  tutor_telegram_url?: string;
};

type Lesson = {
  id: number;
  lesson_date: string;
  lesson_time: string;
  duration_minutes: number;
  status: string;
  is_conducted: boolean;
  meeting_url?: string;
  board_url?: string;
  board_title?: string;
  can_request_reschedule?: boolean;
  reschedule_status?: string;
};

type HomeworkItem = {
  id: number;
  lesson_date: string;
  preview: string;
  tasks_count?: number;
  due_date?: string | null;
  has_submission: boolean;
  submission_status?: string;
};

export function PortalHome({
  student,
  nextLesson,
  pendingHomework,
  onOpenTab,
  onOpenHomework,
}: {
  student: Student;
  nextLesson: Lesson | null;
  pendingHomework: HomeworkItem[];
  onOpenTab: (t: PortalTab) => void;
  onOpenHomework: (id: number) => void;
}) {
  const showBalance = student.show_balance === true;

  return (
    <>
      <PortalCard className="overflow-hidden">
        <div className="bg-gradient-to-br from-brand-blue to-[#2a4db0] px-5 py-5 text-white">
          <p className="text-sm text-white/75">Привет,</p>
          <h2 className="text-2xl font-bold tracking-tight">{student.name}</h2>
          <p className="text-sm text-white/80 mt-1">
            {[student.subject, student.grade].filter(Boolean).join(" · ")}
            {student.tutor_name ? ` · ${student.tutor_name}` : ""}
          </p>
          <div className="mt-4">
            {showBalance ? (
              <>
                <p className="text-[11px] uppercase tracking-wide text-white/60">Баланс</p>
                <p className="text-lg font-semibold">{formatMoney(student.balance)}</p>
              </>
            ) : (
              <p className="text-sm text-white/75">Оплату обычно вносит родитель</p>
            )}
          </div>
        </div>
      </PortalCard>

      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => onOpenTab("homework")}
          className="rounded-2xl border border-slate-200/80 bg-white p-4 text-left shadow-sm hover:border-brand-green/40 transition"
        >
          <p className="text-2xl font-bold text-brand-blue">{pendingHomework.length}</p>
          <p className="text-sm text-slate-600 mt-0.5">ДЗ ждут сдачи</p>
        </button>
        <button
          type="button"
          onClick={() => onOpenTab("progress")}
          className="rounded-2xl border border-slate-200/80 bg-white p-4 text-left shadow-sm hover:border-brand-blue/30 transition"
        >
          <p className="text-sm font-semibold text-brand-blue">Прогресс</p>
          <p className="text-sm text-slate-500 mt-1">Темы и оценки</p>
        </button>
      </div>

      {student.tutor_telegram_url && (
        <a
          href={student.tutor_telegram_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between gap-3 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-900"
        >
          <span>Написать репетитору</span>
          <span aria-hidden>→</span>
        </a>
      )}

      <PortalCard className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-800">Ближайший урок</h3>
          <button
            type="button"
            onClick={() => onOpenTab("schedule")}
            className="text-xs font-medium text-brand-blue"
          >
            Все →
          </button>
        </div>
        {nextLesson ? (
          <div className="space-y-3">
            <div className="flex gap-3 items-center">
              <div
                className={`w-14 shrink-0 rounded-xl text-center py-2 ${
                  isToday(nextLesson.lesson_date)
                    ? "bg-brand-green/15 text-emerald-800"
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                <p className="text-[10px] font-semibold uppercase">
                  {formatRuWeekday(nextLesson.lesson_date)}
                </p>
                <p className="text-lg font-bold leading-tight">
                  {new Date(nextLesson.lesson_date).getDate()}
                </p>
              </div>
              <div className="min-w-0">
                <p className="font-medium text-slate-800">
                  {formatRuDate(nextLesson.lesson_date)}
                  {isToday(nextLesson.lesson_date) && (
                    <span className="ml-2 text-xs font-semibold text-brand-green">сегодня</span>
                  )}
                </p>
                <p className="text-sm text-slate-500">
                  {formatLessonTime(nextLesson.lesson_time)} · {nextLesson.duration_minutes} мин
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {nextLesson.meeting_url ? (
                <a
                  href={nextLesson.meeting_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2.5 rounded-xl bg-brand-green text-white text-sm font-semibold"
                >
                  Войти в урок
                </a>
              ) : (
                <p className="text-xs text-slate-500">Ссылка на урок появится здесь, когда репетитор её добавит</p>
              )}
              {nextLesson.board_url && (
                <a
                  href={nextLesson.board_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700"
                >
                  Доска
                </a>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Ближайших занятий пока нет</p>
        )}
      </PortalCard>

      <PortalCard className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-800">Домашние задания</h3>
          <button
            type="button"
            onClick={() => onOpenTab("homework")}
            className="text-xs font-medium text-brand-blue"
          >
            Все →
          </button>
        </div>
        {pendingHomework.length === 0 ? (
          <p className="text-sm text-slate-500">Все сдано — отличная работа!</p>
        ) : (
          <ul className="space-y-2">
            {pendingHomework.slice(0, 3).map((h) => {
              const due = homeworkDueLabel(h.due_date, h.lesson_date);
              return (
                <li key={h.id}>
                  <button
                    type="button"
                    onClick={() => onOpenHomework(h.id)}
                    className="w-full text-left p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition"
                  >
                    <div className="flex justify-between gap-2 items-center">
                      <span className="text-sm font-medium text-slate-800">
                        {formatRuDate(h.lesson_date)}
                        {due?.urgent && (
                          <span
                            className={`ml-2 text-[10px] font-semibold uppercase ${
                              due.overdue ? "text-rose-700" : "text-amber-700"
                            }`}
                          >
                            {due.text}
                          </span>
                        )}
                      </span>
                      <span
                        className={`text-[11px] font-medium px-2 py-0.5 rounded-lg ${submissionChipClass(
                          h.submission_status || "not_submitted"
                        )}`}
                      >
                        {SUBMISSION_STATUS_LABEL[h.submission_status || "not_submitted"] ||
                          h.submission_status}
                      </span>
                    </div>
                    {h.preview && (
                      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{h.preview}</p>
                    )}
                    <p className="text-[11px] font-semibold text-brand-blue mt-1.5">Открыть →</p>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </PortalCard>
    </>
  );
}

export function PortalSchedule({
  lessons,
  calendarUrl,
  onRequestReschedule,
}: {
  lessons: Lesson[];
  calendarUrl: string;
  onRequestReschedule: (lesson: Lesson) => void;
}) {
  const upcoming = lessons.filter((l) => !l.is_conducted);
  const past = lessons.filter((l) => l.is_conducted);

  return (
    <>
      <PortalCard className="p-4 flex items-center justify-between gap-3">
        <div>
          <p className="font-medium text-slate-800">Календарь</p>
          <p className="text-xs text-slate-500">Добавить в телефон / Google</p>
        </div>
        <a
          href={calendarUrl}
          className="px-3 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium shrink-0"
        >
          .ics
        </a>
      </PortalCard>

      <PortalCard>
        <div className="px-5 pt-4 pb-2">
          <h3 className="font-semibold text-slate-800">Предстоящие</h3>
        </div>
        {upcoming.length === 0 ? (
          <PortalEmpty title="Нет предстоящих уроков" hint="Репетитор назначит занятие" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {upcoming.map((l) => (
              <li key={l.id} className="px-5 py-3.5 space-y-2.5">
                <div className="flex gap-3 items-center">
                  <div
                    className={`w-12 shrink-0 rounded-xl text-center py-1.5 ${
                      isToday(l.lesson_date) ? "bg-emerald-50 text-emerald-800" : "bg-slate-50 text-slate-700"
                    }`}
                  >
                    <p className="text-[10px] font-semibold uppercase">{formatRuWeekday(l.lesson_date)}</p>
                    <p className="text-base font-bold leading-tight">{new Date(l.lesson_date).getDate()}</p>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800">{formatRuDate(l.lesson_date)}</p>
                    <p className="text-sm text-slate-500">
                      {formatLessonTime(l.lesson_time)} · {l.duration_minutes} мин
                    </p>
                    {l.reschedule_status === "pending" && (
                      <p className="text-[11px] text-amber-700 font-medium mt-0.5">Запрос на перенос отправлен</p>
                    )}
                    {l.reschedule_status === "approved" && (
                      <p className="text-[11px] text-emerald-700 font-medium mt-0.5">Перенос согласован</p>
                    )}
                    {l.reschedule_status === "rejected" && (
                      <p className="text-[11px] text-slate-500 mt-0.5">Перенос отклонён</p>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {l.meeting_url && (
                    <a
                      href={l.meeting_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-2 rounded-xl bg-brand-green text-white text-xs font-semibold"
                    >
                      Войти в урок
                    </a>
                  )}
                  {l.board_url && (
                    <a
                      href={l.board_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700"
                    >
                      {l.board_title || "Доска"}
                    </a>
                  )}
                  {l.can_request_reschedule && (
                    <button
                      type="button"
                      onClick={() => onRequestReschedule(l)}
                      className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600"
                    >
                      Перенести
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </PortalCard>

      {past.length > 0 && (
        <PortalCard>
          <div className="px-5 pt-4 pb-2">
            <h3 className="font-semibold text-slate-500">Прошедшие</h3>
          </div>
          <ul className="divide-y divide-slate-100">
            {past.slice(0, 8).map((l) => (
              <li key={l.id} className="px-5 py-3 flex justify-between items-center gap-2 text-sm text-slate-500">
                <span>{formatRuDate(l.lesson_date)}</span>
                <span className="flex items-center gap-2">
                  <span>{formatLessonTime(l.lesson_time)}</span>
                  {l.board_url && (
                    <a
                      href={l.board_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-semibold text-brand-blue"
                    >
                      Доска
                    </a>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </PortalCard>
      )}
    </>
  );
}
