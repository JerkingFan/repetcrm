"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { sanitizeHomeworkHtml } from "@/lib/sanitizeHtml";
import {
  AI_VERDICT_LABEL,
  aiVerdictBoxClass,
  formatRuDate,
  formatRuWeekday,
  homeworkDueLabel,
  isToday,
  submissionChipClass,
  SUBMISSION_STATUS_LABEL,
} from "@/lib/portalUi";
import { PortalCard, PortalEmpty } from "./PortalShell";
import ConfettiBurst from "./ConfettiBurst";

type HomeworkItem = {
  id: number;
  lesson_date: string;
  preview: string;
  tasks_count?: number;
  due_date?: string | null;
  has_submission: boolean;
  submission_status?: string;
};

type Submission = {
  id: number;
  original_filename: string;
  submitted_at: string;
  status?: string;
  comment?: string;
  tutor_comment?: string;
  ai_review_status?: string;
  ai_verdict?: string;
  ai_score?: number | null;
  ai_feedback?: string;
  ai_review_error?: string;
};

type HomeworkDetail = {
  id: number;
  lesson_date: string;
  homework_text: string;
  preview_html?: string;
  due_date?: string | null;
  board_url?: string;
  meeting_url?: string;
  tutor_telegram_url?: string;
  submissions: Submission[];
};

type Filter = "all" | "todo" | "done";

function statusOf(h: HomeworkItem): string {
  return h.submission_status || (h.has_submission ? "submitted" : "not_submitted");
}

function isTodo(h: HomeworkItem): boolean {
  const s = statusOf(h);
  return s === "not_submitted" || s === "needs_revision";
}

export default function PortalHomework({
  items,
  selectedId,
  detail,
  comment,
  uploading,
  onSelect,
  onBack,
  onCommentChange,
  onSubmitFile,
}: {
  items: HomeworkItem[];
  selectedId: number | null;
  detail: HomeworkDetail | null;
  comment: string;
  uploading: boolean;
  onSelect: (id: number) => void;
  onBack: () => void;
  onCommentChange: (v: string) => void;
  onSubmitFile: (file: File) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [expanded, setExpanded] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  useEffect(() => {
    setExpanded(false);
    setDownloadError("");
  }, [selectedId]);

  const downloadSubmission = async (submissionId: number, filename: string) => {
    if (!selectedId) return;
    setDownloadError("");
    try {
      const res = await fetch(api.portal.submissionFileUrl(selectedId, submissionId), {
        credentials: "include",
      });
      if (!res.ok) {
        setDownloadError("Не удалось скачать файл");
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      setDownloadError("Не удалось скачать файл");
    }
  };

  const todoCount = items.filter(isTodo).length;
  const doneCount = items.length - todoCount;

  const filtered = useMemo(() => {
    if (filter === "todo") return items.filter(isTodo);
    if (filter === "done") return items.filter((h) => !isTodo(h));
    return items;
  }, [items, filter]);

  if (selectedId && detail) {
    const latest = detail.submissions[0];
    const status = latest?.status || "not_submitted";
    const due = homeworkDueLabel(detail.due_date, detail.lesson_date);
    const needHelp =
      status === "needs_revision" ||
      latest?.ai_verdict === "incorrect" ||
      latest?.ai_verdict === "partially_correct";
    const celebrate =
      latest?.ai_review_status === "done" &&
      (latest.ai_verdict === "correct" || (latest.ai_score != null && latest.ai_score >= 85));

    const shareText =
      `Привет! Проверил ДЗ за ${formatRuDate(detail.lesson_date)}.\n` +
      `${AI_VERDICT_LABEL[latest?.ai_verdict || ""] || latest?.ai_verdict || ""}` +
      (latest?.ai_score != null && latest?.ai_verdict !== "unclear" ? ` · ${latest.ai_score}%` : "") +
      (latest?.ai_feedback ? `\n\n${latest.ai_feedback.slice(0, 400)}` : "");

    const tutorShareHref = detail.tutor_telegram_url
      ? `${detail.tutor_telegram_url}${detail.tutor_telegram_url.includes("?") ? "&" : "?"}text=${encodeURIComponent(shareText)}`
      : "";

    return (
      <>
        <ConfettiBurst active={celebrate} />
        <button
          type="button"
          onClick={onBack}
          className="text-sm font-medium text-brand-blue inline-flex items-center gap-1.5"
        >
          <span aria-hidden>←</span> К списку ДЗ
        </button>

        <PortalCard className="overflow-hidden">
          <div className="bg-gradient-to-r from-brand-blue to-[#2f56c9] px-5 py-4 text-white">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-wide text-white/70 font-semibold">
                  Домашнее задание
                </p>
                <h2 className="text-xl font-bold mt-0.5">
                  {formatRuDate(detail.lesson_date, {
                    day: "numeric",
                    month: "long",
                    weekday: "short",
                  })}
                </h2>
                {due && (
                  <p className={`text-sm mt-1 ${due.urgent ? "text-amber-100" : "text-white/75"}`}>
                    {due.overdue ? "Просрочено · " : ""}
                    {due.text}
                  </p>
                )}
              </div>
              <span
                className={`text-[11px] font-semibold px-2.5 py-1 rounded-full shrink-0 ${
                  status === "reviewed"
                    ? "bg-emerald-400/25 text-white"
                    : status === "needs_revision"
                      ? "bg-amber-300/30 text-white"
                      : status === "submitted"
                        ? "bg-white/20 text-white"
                        : "bg-white/15 text-white/90"
                }`}
              >
                {SUBMISSION_STATUS_LABEL[status] || status}
              </span>
            </div>
          </div>

          <div className="p-4 sm:p-5">
            <div
              className={`portal-hw prose prose-sm max-w-none text-slate-800 overflow-hidden transition-[max-height] ${
                expanded ? "max-h-none" : "max-h-72"
              }`}
            >
              <div
                dangerouslySetInnerHTML={{
                  __html: sanitizeHomeworkHtml(detail.preview_html || detail.homework_text),
                }}
              />
            </div>
            {!expanded && (
              <div className="relative -mt-10 h-10 bg-gradient-to-t from-white to-transparent pointer-events-none" />
            )}
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="mt-1 text-sm font-semibold text-brand-blue"
            >
              {expanded ? "Свернуть задание" : "Показать полностью"}
            </button>

            {(detail.board_url || detail.meeting_url) && (
              <div className="mt-4 flex flex-wrap gap-2">
                {detail.board_url && (
                  <a
                    href={detail.board_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-2 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700"
                  >
                    Материалы / доска
                  </a>
                )}
                {detail.meeting_url && (
                  <a
                    href={detail.meeting_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-2 rounded-xl bg-brand-green text-white text-sm font-semibold"
                  >
                    Войти в урок
                  </a>
                )}
              </div>
            )}
          </div>
        </PortalCard>

        {(latest?.tutor_comment ||
          latest?.ai_review_status === "done" ||
          latest?.ai_review_status === "pending" ||
          latest?.ai_review_status === "running" ||
          latest?.ai_review_status === "error" ||
          latest?.ai_review_status === "skipped") && (
          <PortalCard className="p-4 space-y-3">
            <h3 className="font-semibold text-slate-800 text-sm">Результат проверки</h3>
            {latest?.tutor_comment && (
              <div className="p-3 rounded-xl bg-brand-blue/5 border border-brand-blue/15 text-sm text-slate-800">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-blue mb-1">
                  Комментарий репетитора
                </p>
                {latest.tutor_comment}
              </div>
            )}
            {(latest.ai_review_status === "pending" || latest.ai_review_status === "running") && (
              <div className="p-4 rounded-xl border border-sky-200 bg-sky-50 text-sm text-sky-950 ai-checking">
                <div className="flex items-center gap-2">
                  <span className="inline-block w-2.5 h-2.5 rounded-full bg-sky-500 animate-pulse" />
                  <p className="font-semibold">AI проверяет решение…</p>
                </div>
                <p className="mt-1 text-sky-800/80 text-xs">Обычно 10–30 секунд</p>
              </div>
            )}
            {latest.ai_review_status === "done" && latest.ai_verdict && (
              <div className={`p-4 rounded-xl border text-sm ${aiVerdictBoxClass(latest.ai_verdict)}`}>
                <p className="font-bold text-base">
                  {AI_VERDICT_LABEL[latest.ai_verdict] || latest.ai_verdict}
                  {latest.ai_verdict !== "unclear" && latest.ai_score != null
                    ? ` · ${latest.ai_score}%`
                    : ""}
                </p>
                {latest.ai_feedback && (
                  <p className="mt-2 leading-relaxed whitespace-pre-wrap">{latest.ai_feedback}</p>
                )}
                <p className="mt-3 text-xs opacity-75">
                  Предварительная оценка AI. Репетитор может подтвердить или изменить.
                </p>
                {detail.tutor_telegram_url && (
                  <a
                    href={tutorShareHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-flex w-full justify-center px-3 py-2.5 rounded-xl bg-[#229ED9] text-white text-sm font-semibold"
                  >
                    Показать репетитору в Telegram
                  </a>
                )}
              </div>
            )}
            {latest.ai_review_status === "skipped" && latest.ai_feedback && (
              <p className="text-sm text-slate-500 bg-slate-50 rounded-xl p-3">{latest.ai_feedback}</p>
            )}
            {latest.ai_review_status === "error" && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-900">
                Автопроверка не сработала — репетитор проверит вручную.
              </div>
            )}
          </PortalCard>
        )}

        {detail.tutor_telegram_url && (
          <a
            href={detail.tutor_telegram_url}
            target="_blank"
            rel="noopener noreferrer"
            className={`block w-full text-center px-4 py-3 rounded-xl text-sm font-semibold ${
              needHelp
                ? "bg-sky-600 text-white"
                : "border border-slate-200 bg-white text-brand-blue"
            }`}
          >
            {needHelp ? "Написать репетитору" : "Есть вопрос? Написать репетитору"}
          </a>
        )}

        <PortalCard className="p-5 space-y-4">
          <div>
            <h3 className="font-semibold text-slate-800">Сдать решение</h3>
            <p className="text-sm text-slate-500 mt-0.5">
              Сфотографируйте тетрадь при хорошем свете. AI проверяет фото (не PDF).
            </p>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) onSubmitFile(f);
            }}
            className={`rounded-2xl border-2 border-dashed p-5 text-center transition ${
              dragOver ? "border-brand-green bg-emerald-50" : "border-slate-200 bg-slate-50/90"
            }`}
          >
            <div className="mx-auto w-12 h-12 rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-brand-blue mb-3 shadow-sm">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
                />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-800">
              {uploading ? "Отправляем…" : "Загрузите фото решения"}
            </p>
            <p className="text-xs text-slate-500 mt-1">JPG, PNG, WebP · до 15 МБ</p>
            <div className="mt-4 flex flex-col sm:flex-row justify-center gap-2">
              <button
                type="button"
                disabled={uploading}
                onClick={() => cameraRef.current?.click()}
                className="px-4 py-3 rounded-xl bg-brand-blue text-white text-sm font-semibold disabled:opacity-50"
              >
                Открыть камеру
              </button>
              <button
                type="button"
                disabled={uploading}
                onClick={() => fileRef.current?.click()}
                className="px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700 disabled:opacity-50"
              >
                Выбрать файл
              </button>
            </div>
            <input
              ref={cameraRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onSubmitFile(f);
                e.target.value = "";
              }}
            />
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onSubmitFile(f);
                e.target.value = "";
              }}
            />
          </div>

          <input
            type="text"
            placeholder="Комментарий к решению (необязательно)"
            value={comment}
            onChange={(e) => onCommentChange(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue"
          />

          {detail.submissions.length > 0 && (
            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
                История отправок
              </p>
              {downloadError && (
                <p className="text-xs text-red-600 mb-2">{downloadError}</p>
              )}
              <ul className="space-y-2">
                {detail.submissions.map((s) => (
                  <li
                    key={s.id}
                    className="flex justify-between gap-2 text-sm text-slate-600 bg-slate-50 rounded-xl px-3 py-2.5"
                  >
                    <button
                      type="button"
                      onClick={() => downloadSubmission(s.id, s.original_filename)}
                      className="truncate font-medium text-left text-brand-blue hover:underline"
                      title="Скачать файл"
                    >
                      {s.original_filename}
                    </button>
                    <span className="text-xs text-slate-400 shrink-0">
                      {new Date(s.submitted_at).toLocaleString("ru-RU", {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </PortalCard>
      </>
    );
  }

  return (
    <>
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {(
          [
            { id: "all" as const, label: "Все", count: items.length },
            { id: "todo" as const, label: "Сдать", count: todoCount },
            { id: "done" as const, label: "Готово", count: doneCount },
          ] as const
        ).map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={`shrink-0 px-3.5 py-2 rounded-full text-sm font-semibold border transition ${
              filter === f.id
                ? "bg-brand-blue text-white border-brand-blue"
                : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
            }`}
          >
            {f.label}
            <span
              className={`ml-1.5 text-xs ${filter === f.id ? "text-white/80" : "text-slate-400"}`}
            >
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <PortalCard>
          <PortalEmpty
            title={filter === "todo" ? "Всё сдано" : "Пока нет заданий"}
            hint={
              filter === "todo"
                ? "Новые ДЗ появятся после урока"
                : "Репетитор подготовит домашнее задание"
            }
          />
        </PortalCard>
      ) : (
        <ul className="space-y-3">
          {filtered.map((h) => {
            const st = statusOf(h);
            const todo = isTodo(h);
            const due = homeworkDueLabel(h.due_date, h.lesson_date);
            return (
              <li key={h.id}>
                <button
                  type="button"
                  onClick={() => onSelect(h.id)}
                  className={`w-full text-left rounded-2xl border bg-white p-4 shadow-sm shadow-slate-200/40 transition hover:border-brand-blue/30 hover:shadow-md portal-rise ${
                    todo ? "border-amber-200/80" : "border-slate-200/80"
                  }`}
                >
                  <div className="flex gap-3">
                    <div
                      className={`w-12 shrink-0 rounded-xl text-center py-1.5 ${
                        isToday(h.lesson_date)
                          ? "bg-brand-green/15 text-emerald-800"
                          : todo
                            ? "bg-amber-50 text-amber-900"
                            : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      <p className="text-[10px] font-semibold uppercase">
                        {formatRuWeekday(h.lesson_date)}
                      </p>
                      <p className="text-lg font-bold leading-tight">
                        {new Date(h.lesson_date).getDate()}
                      </p>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-900 truncate">
                            {formatRuDate(h.lesson_date)}
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {due
                              ? due.text
                              : h.tasks_count && h.tasks_count > 0
                                ? `${h.tasks_count} ${
                                    h.tasks_count === 1
                                      ? "задача"
                                      : h.tasks_count < 5
                                        ? "задачи"
                                        : "задач"
                                  }`
                                : "Домашнее задание"}
                          </p>
                        </div>
                        <span
                          className={`text-[11px] font-semibold px-2 py-1 rounded-lg shrink-0 ${submissionChipClass(
                            st
                          )}`}
                        >
                          {SUBMISSION_STATUS_LABEL[st] || st}
                        </span>
                      </div>
                      {h.preview && (
                        <p className="text-sm text-slate-600 mt-2 line-clamp-2 leading-snug">
                          {h.preview}
                        </p>
                      )}
                      <p className="text-xs font-semibold text-brand-blue mt-2.5">
                        {todo ? "Открыть и сдать →" : "Открыть →"}
                      </p>
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
