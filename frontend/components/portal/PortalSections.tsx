"use client";

import type { CSSProperties } from "react";
import { formatLessonTime } from "@/lib/calendar";
import { formatMoney } from "@/lib/currency";
import { avatarEmoji } from "@/lib/portalTheme";
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
  display_name?: string;
  subject: string;
  grade: string;
  balance: number;
  show_balance?: boolean;
  tutor_name: string;
  tutor_telegram_url?: string;
  portal_avatar?: string;
  portal_theme?: string;
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
  streakDays,
  onOpenTab,
  onOpenHomework,
  onOpenFocus,
}: {
  student: Student;
  nextLesson: Lesson | null;
  pendingHomework: HomeworkItem[];
  streakDays?: number;
  onOpenTab: (t: PortalTab) => void;
  onOpenHomework: (id: number) => void;
  onOpenFocus?: () => void;
}) {
  const showBalance = student.show_balance === true;
  const display = student.display_name || student.name;
  const meta = [student.subject, student.grade].filter(Boolean).join(" · ");

  return (
    <>
      {/* Hero — one composition */}
      <section className="portal-hero portal-rise overflow-hidden relative">
        <div className="portal-hero-shine" aria-hidden />
        <div className="relative z-10 px-5 pt-6 pb-5 text-white">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold tracking-[0.22em] uppercase text-white/55">
                Привет
              </p>
              <h2 className="portal-hero-name mt-1 truncate">{display}</h2>
              <p className="text-sm text-white/70 mt-1.5 truncate">
                {meta}
                {student.tutor_name ? ` · ${student.tutor_name}` : ""}
              </p>
            </div>
            <div className="portal-avatar-ring shrink-0" aria-hidden>
              <span className="text-2xl leading-none">{avatarEmoji(student.portal_avatar)}</span>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-end gap-3">
            {(streakDays ?? 0) > 0 && (
              <button
                type="button"
                onClick={() => onOpenTab("progress")}
                className="portal-streak-chip"
              >
                <span className="text-lg font-black tabular-nums leading-none">{streakDays}</span>
                <span className="text-[11px] font-semibold leading-tight opacity-90">
                  {streakDays === 1 ? "день" : "серия"}
                </span>
              </button>
            )}
            {showBalance && (
              <div className="ml-auto text-right">
                <p className="text-[10px] uppercase tracking-wider text-white/50">Баланс</p>
                <p className="text-base font-semibold tabular-nums">{formatMoney(student.balance)}</p>
              </div>
            )}
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2.5">
            <button type="button" onClick={() => onOpenTab("homework")} className="portal-hero-cta">
              <span className="text-2xl font-black tabular-nums leading-none">
                {pendingHomework.length}
              </span>
              <span className="text-[11px] font-semibold text-white/75 mt-1">ДЗ ждут</span>
            </button>
            <button type="button" onClick={() => onOpenFocus?.()} className="portal-hero-cta portal-hero-cta-focus">
              <span className="text-sm font-bold tracking-tight">Фокус</span>
              <span className="text-[11px] font-medium text-white/70 mt-1">Lo-fi · решить</span>
            </button>
          </div>
        </div>
      </section>

      {student.tutor_telegram_url && (
        <a
          href={student.tutor_telegram_url}
          target="_blank"
          rel="noopener noreferrer"
          className="portal-link-row portal-rise"
          style={{ animationDelay: "60ms" }}
        >
          <span>Написать репетитору</span>
          <span className="portal-link-arrow" aria-hidden>
            →
          </span>
        </a>
      )}

      <PortalCard className="p-5 portal-rise" style={{ animationDelay: "90ms" } as CSSProperties}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="portal-section-title">Ближайший урок</h3>
          <button type="button" onClick={() => onOpenTab("schedule")} className="portal-text-link">
            Все →
          </button>
        </div>
        {nextLesson ? (
          <div className="space-y-3.5">
            <div className="flex gap-3.5 items-center">
              <div className={`portal-date-block ${isToday(nextLesson.lesson_date) ? "is-today" : ""}`}>
                <p className="text-[10px] font-bold uppercase tracking-wide opacity-70">
                  {formatRuWeekday(nextLesson.lesson_date)}
                </p>
                <p className="text-2xl font-black leading-none tabular-nums">
                  {new Date(nextLesson.lesson_date).getDate()}
                </p>
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-slate-900">
                  {formatRuDate(nextLesson.lesson_date)}
                  {isToday(nextLesson.lesson_date) && (
                    <span className="ml-2 text-[11px] font-bold text-[var(--portal-accent)]">сегодня</span>
                  )}
                </p>
                <p className="text-sm text-slate-500 mt-0.5">
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
                  className="portal-btn-primary"
                >
                  Войти в урок
                </a>
              ) : (
                <p className="text-xs text-slate-500">Ссылка появится, когда репетитор её добавит</p>
              )}
              {nextLesson.board_url && (
                <a
                  href={nextLesson.board_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="portal-btn-ghost"
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

      <PortalCard className="p-5 portal-rise" style={{ animationDelay: "130ms" } as CSSProperties}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="portal-section-title">Домашние задания</h3>
          <button type="button" onClick={() => onOpenTab("homework")} className="portal-text-link">
            Все →
          </button>
        </div>
        {pendingHomework.length === 0 ? (
          <p className="text-sm text-slate-500">Все сдано — отличная работа</p>
        ) : (
          <ul className="space-y-2">
            {pendingHomework.slice(0, 3).map((h) => {
              const due = homeworkDueLabel(h.due_date, h.lesson_date);
              return (
                <li key={h.id}>
                  <button type="button" onClick={() => onOpenHomework(h.id)} className="portal-hw-row">
                    <div className="flex justify-between gap-2 items-center">
                      <span className="text-sm font-semibold text-slate-900">
                        {formatRuDate(h.lesson_date)}
                        {due?.urgent && (
                          <span
                            className={`ml-2 text-[10px] font-bold uppercase ${
                              due.overdue ? "text-rose-600" : "text-amber-700"
                            }`}
                          >
                            {due.text}
                          </span>
                        )}
                      </span>
                      <span
                        className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${submissionChipClass(
                          h.submission_status || "not_submitted"
                        )}`}
                      >
                        {SUBMISSION_STATUS_LABEL[h.submission_status || "not_submitted"] ||
                          h.submission_status}
                      </span>
                    </div>
                    {h.preview && (
                      <p className="text-xs text-slate-500 mt-1.5 line-clamp-2 leading-relaxed">
                        {h.preview}
                      </p>
                    )}
                    <p className="text-[11px] font-bold text-[var(--portal-accent)] mt-2">Открыть →</p>
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
      <PortalCard className="p-4 flex items-center justify-between gap-3 portal-rise">
        <div>
          <p className="portal-section-title">Календарь</p>
          <p className="text-xs text-slate-500 mt-0.5">Добавить в телефон / Google</p>
        </div>
        <a href={calendarUrl} className="portal-btn-primary shrink-0 !py-2 !px-3 text-sm">
          .ics
        </a>
      </PortalCard>

      <PortalCard className="portal-rise" style={{ animationDelay: "60ms" } as CSSProperties}>
        <div className="px-5 pt-4 pb-2">
          <h3 className="portal-section-title">Предстоящие</h3>
        </div>
        {upcoming.length === 0 ? (
          <PortalEmpty title="Нет предстоящих уроков" hint="Репетитор назначит занятие" />
        ) : (
          <ul className="divide-y divide-slate-100/80">
            {upcoming.map((l) => (
              <li key={l.id} className="px-5 py-3.5 space-y-2.5">
                <div className="flex gap-3 items-center">
                  <div className={`portal-date-block !w-12 ${isToday(l.lesson_date) ? "is-today" : ""}`}>
                    <p className="text-[10px] font-bold uppercase opacity-70">
                      {formatRuWeekday(l.lesson_date)}
                    </p>
                    <p className="text-lg font-black leading-none tabular-nums">
                      {new Date(l.lesson_date).getDate()}
                    </p>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-900">{formatRuDate(l.lesson_date)}</p>
                    <p className="text-sm text-slate-500">
                      {formatLessonTime(l.lesson_time)} · {l.duration_minutes} мин
                    </p>
                    {l.reschedule_status === "pending" && (
                      <p className="text-[11px] text-amber-700 font-semibold mt-0.5">
                        Запрос на перенос отправлен
                      </p>
                    )}
                    {l.reschedule_status === "approved" && (
                      <p className="text-[11px] text-emerald-700 font-semibold mt-0.5">Перенос согласован</p>
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
                      className="portal-btn-primary !text-xs !py-2 !px-3"
                    >
                      Войти в урок
                    </a>
                  )}
                  {l.board_url && (
                    <a
                      href={l.board_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="portal-btn-ghost !text-xs !py-2 !px-3"
                    >
                      {l.board_title || "Доска"}
                    </a>
                  )}
                  {l.can_request_reschedule && (
                    <button
                      type="button"
                      onClick={() => onRequestReschedule(l)}
                      className="portal-btn-ghost !text-xs !py-2 !px-3"
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
        <PortalCard className="portal-rise" style={{ animationDelay: "100ms" } as CSSProperties}>
          <div className="px-5 pt-4 pb-2">
            <h3 className="portal-section-title text-slate-500">Прошедшие</h3>
          </div>
          <ul className="divide-y divide-slate-100/80">
            {past.slice(0, 8).map((l) => (
              <li
                key={l.id}
                className="px-5 py-3 flex justify-between items-center gap-2 text-sm text-slate-500"
              >
                <span>{formatRuDate(l.lesson_date)}</span>
                <span className="flex items-center gap-2">
                  <span>{formatLessonTime(l.lesson_time)}</span>
                  {l.board_url && (
                    <a
                      href={l.board_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-bold text-[var(--portal-accent)]"
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
