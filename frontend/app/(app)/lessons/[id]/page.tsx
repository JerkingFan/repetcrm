"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  PlusIcon,
  TrashIcon,
  SparklesIcon,
  ArrowDownTrayIcon,
  PencilIcon,
} from "@heroicons/react/24/outline";
import LessonFormModal, { LessonFormData } from "@/components/LessonFormModal";
import { formatLessonTime } from "@/lib/calendar";
import { api, ApiError, authFetch } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import LoadError from "@/components/LoadError";
import Alert from "@/components/Alert";
import { sanitizeHomeworkHtml } from "@/lib/sanitizeHtml";
import LessonHomeworkForm from "@/components/LessonHomeworkForm";
import { defaultHomeworkPrefs, HomeworkPrefs } from "@/lib/homeworkPrefs";
import { formatMoney } from "@/lib/currency";
import { pollJobUntilDone, JOB_POLL_INTERVAL_MS, JOB_TIMEOUT_MS, JOB_TIMEOUT_MESSAGE } from "@/lib/jobPoll";
import HomeworkTemplatesPanel from "@/components/HomeworkTemplatesPanel";
import VoiceBriefButton from "@/components/VoiceBriefButton";
import TrialFollowupBanner from "@/components/TrialFollowupBanner";

type ChecklistRow = {
  topic: string;
  work_type: string;
  difficulty: string;
  understanding: number;
};

type Lesson = {
  id: number;
  student_id: number;
  board_id?: number | null;
  student_name?: string;
  lesson_date: string;
  lesson_time?: string;
  duration_minutes: number;
  payment_amount: number;
  is_paid: boolean;
  notes: string;
  meeting_url?: string;
  checklist_items: Array<ChecklistRow & { id?: number }>;
  homework?: { id: number; homework_text: string; due_date?: string | null };
  is_conducted?: boolean;
  homework_prefs?: HomeworkPrefs;
};

const emptyRow = (): ChecklistRow => ({
  topic: "",
  work_type: "practice",
  difficulty: "medium",
  understanding: 3,
});

export default function LessonDetailPage() {
  const params = useParams();
  const lessonId = Number(params.id);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [rows, setRows] = useState<ChecklistRow[]>([emptyRow()]);
  const [homeworkHtml, setHomeworkHtml] = useState("");
  const [homeworkDisplayHtml, setHomeworkDisplayHtml] = useState("");
  const [homeworkId, setHomeworkId] = useState<number | null>(null);
  const [homeworkDueDate, setHomeworkDueDate] = useState("");
  const [homeworkView, setHomeworkView] = useState<"latex" | "preview">("preview");
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfStatus, setPdfStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<"idle" | "queued" | "running" | "done" | "error">("idle");
  const [jobHint, setJobHint] = useState("");
  const [showEdit, setShowEdit] = useState(false);
  const [isConducted, setIsConducted] = useState(false);
  const [prefs, setPrefs] = useState<HomeworkPrefs>(defaultHomeworkPrefs());
  const [showOptional, setShowOptional] = useState(true);
  const [submissions, setSubmissions] = useState<
    Awaited<ReturnType<typeof api.homework.submissions>>
  >([]);
  const [reviewComments, setReviewComments] = useState<Record<number, string>>({});
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [togglingPaid, setTogglingPaid] = useState(false);
  const [trialFollowup, setTrialFollowup] = useState("");

  const submissionStatusLabel: Record<string, string> = {
    submitted: "На проверке",
    reviewed: "Проверено",
    needs_revision: "Нужна доработка",
  };

  const aiVerdictLabel: Record<string, string> = {
    correct: "Верно",
    partially_correct: "Частично верно",
    incorrect: "Неверно",
    unclear: "Не удалось оценить",
  };

  const loadSubmissions = useCallback((hwId: number) => {
    api.homework.submissions(hwId).then(setSubmissions).catch(() => setSubmissions([]));
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError("");
    api.lessons
      .get<Lesson>(lessonId)
      .then((l) => {
        setLesson(l);
        if (l.checklist_items?.length) {
          setRows(
            l.checklist_items.map((i) => ({
              topic: i.topic,
              work_type: i.work_type,
              difficulty: i.difficulty,
              understanding: i.understanding,
            }))
          );
        }
        setIsConducted(!!l.is_conducted);
        setPrefs(
          l.homework_prefs ? { ...defaultHomeworkPrefs(), ...l.homework_prefs } : defaultHomeworkPrefs()
        );
        if (l.homework) {
          setHomeworkHtml(l.homework.homework_text);
          setHomeworkId(l.homework.id);
          setHomeworkDueDate(l.homework.due_date ? l.homework.due_date.slice(0, 10) : "");
          loadSubmissions(l.homework.id);
          api.homework
            .previewHtml(l.homework.id)
            .then((p) => setHomeworkDisplayHtml(p.html))
            .catch(() => setHomeworkDisplayHtml(l.homework!.homework_text));
        } else {
          setHomeworkId(null);
          setHomeworkDueDate("");
          setSubmissions([]);
          setHomeworkDisplayHtml("");
        }
      })
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.message : "Не удалось загрузить урок")
      )
      .finally(() => setLoading(false));
  }, [lessonId, loadSubmissions]);

  useEffect(() => load(), [load]);

  // Resume background generation if user reloads the page
  useEffect(() => {
    if (!lessonId) return;
    const key = `repetcrm:hw_job:${lessonId}`;
    const saved = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
    if (saved) {
      setJobId(saved);
      setJobStatus("queued");
    }
  }, [lessonId]);

  useEffect(() => {
    if (!jobId || jobStatus === "done" || jobStatus === "error") return;
    const key = `repetcrm:hw_job:${lessonId}`;

    let cancelled = false;
    const startedAt = Date.now();

    const tick = async () => {
      if (Date.now() - startedAt > JOB_TIMEOUT_MS) {
        window.localStorage.removeItem(key);
        setJobStatus("error");
        setGenerating(false);
        setError(JOB_TIMEOUT_MESSAGE);
        return;
      }
      try {
        const j = await api.lessons.getJob(jobId);
        if (cancelled) return;
        setJobStatus(j.status);
        if (j.status === "done") {
          window.localStorage.removeItem(key);
          setGenerating(false);
          const hwId = j.result?.homework_id;
          if (hwId) {
            setHomeworkId(hwId);
            load();
          }
          setSuccess(j.result?.generation_hint || "Домашнее задание готово.");
        } else if (j.status === "error") {
          window.localStorage.removeItem(key);
          setGenerating(false);
          setError(j.error || "Ошибка генерации");
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          window.localStorage.removeItem(key);
          setJobStatus("error");
          setGenerating(false);
          setError("Задача не найдена (сервер перезапущен). Нажмите «Сгенерировать» снова.");
        }
      }
    };

    tick();
    const t = window.setInterval(tick, JOB_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [jobId, jobStatus, lessonId, load]);

  useEffect(() => {
    const wt =
      prefs.focus_aspect === "theory"
        ? "theory"
        : prefs.focus_aspect === "errors_review"
          ? "test"
          : "practice";
    const diff =
      prefs.difficulty_level === "basic"
        ? "basic"
        : prefs.difficulty_level === "high"
          ? "advanced"
          : "medium";
    setRows((prev) =>
      prev.map((r) => ({
        ...r,
        work_type: wt,
        difficulty: diff,
        understanding: prefs.understanding_global,
      }))
    );
  }, [prefs.focus_aspect, prefs.difficulty_level, prefs.understanding_global]);

  const saveLessonReport = async (markConducted = isConducted) => {
    const valid = rows.filter((r) => r.topic.trim());
    if (!valid.length) {
      setError("Укажите хотя бы одну тему (вопрос 1)");
      return false;
    }
    if (!prefs.understanding_global || !prefs.student_level) {
      setError("Заполните понимание материала и уровень ученика");
      return false;
    }
    setSaving(true);
    setError("");
    try {
      await api.lessons.saveLessonReport(lessonId, {
        items: valid.map((r) => ({
          topic: r.topic.trim(),
          work_type: r.work_type,
          difficulty: r.difficulty,
          understanding: prefs.understanding_global,
        })),
        prefs,
        is_conducted: markConducted,
      });
      setIsConducted(markConducted);
      setSuccess(markConducted ? "Занятие сохранено, можно генерировать ДЗ" : "Настройки сохранены");
      if (markConducted && lesson?.student_id) {
        api.students
          .trialFollowup(lesson.student_id)
          .then((f) => setTrialFollowup(f.show ? f.message : ""))
          .catch(() => setTrialFollowup(""));
      }
      load();
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
      return false;
    } finally {
      setSaving(false);
    }
  };

  const generate = async () => {
    setGenerating(true);
    setError("");
    setSuccess("");
    try {
      if (!isConducted) {
        setError("Сначала отметьте занятие проведённым и сохраните чек-лист");
        setGenerating(false);
        return;
      }
      const ok = await saveLessonReport(true);
      if (!ok) {
        setGenerating(false);
        return;
      }
      const started = await api.lessons.startHomeworkJob(lessonId);
      const key = `repetcrm:hw_job:${lessonId}`;
      window.localStorage.setItem(key, started.job_id);
      setJobId(started.job_id);
      setJobStatus(started.status === "running" ? "running" : "queued");
      setJobHint("Генерируем домашнее задание в фоне — можно закрыть вкладку, результат сохранится.");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка генерации";
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  const saveHomework = async () => {
    if (!homeworkId) return;
    setSaving(true);
    try {
      await api.homework.update(homeworkId, {
        homework_text: homeworkHtml,
        due_date: homeworkDueDate || null,
      });
      setEditMode(false);
      setSuccess("ДЗ сохранено");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setSaving(false);
    }
  };

  const saveDueDate = async () => {
    if (!homeworkId) return;
    setSaving(true);
    setError("");
    try {
      await api.homework.update(homeworkId, { due_date: homeworkDueDate || null });
      setSuccess(homeworkDueDate ? "Срок сдачи сохранён" : "Срок сдачи снят");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setSaving(false);
    }
  };

  const downloadPython = async () => {
    if (!homeworkId) return;
    const res = await authFetch(api.homework.pythonScriptUrl(homeworkId));
    if (!res.ok) {
      setError("Не удалось скачать Python-скрипт");
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `homework_${lesson?.student_name || "student"}.py`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const downloadLatex = async () => {
    if (!homeworkId) return;
    const res = await authFetch(api.homework.latexUrl(homeworkId));
    if (!res.ok) {
      setError("Не удалось скачать .tex");
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `homework_${lesson?.student_name || "student"}.tex`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const downloadPdf = async () => {
    if (!homeworkId || pdfLoading) return;
    setError("");
    setPdfLoading(true);
    setPdfStatus("Собираем PDF… обычно до 30 секунд");

    const statusSteps = ["Собираем PDF…", "Компилируем формулы…", "Почти готово…"];
    let step = 0;
    const statusTimer = window.setInterval(() => {
      setPdfStatus(statusSteps[Math.min(step, statusSteps.length - 1)]);
      step += 1;
    }, 8000);

    try {
      let res = await authFetch(api.homework.pdfUrl(homeworkId));

      // Совместимость со старым API (202 + job)
      if (res.status === 202) {
        const started = (await res.json()) as { job_id: string };
        setPdfStatus("Собираем PDF…");
        const polled = await pollJobUntilDone(started.job_id, (status) => {
          if (status === "running") setPdfStatus("Компилируем формулы…");
        });
        if (!polled.ok) {
          setError(polled.error || "Ошибка сборки PDF");
          return;
        }
        res = await authFetch(api.homework.pdfUrl(homeworkId));
      }

      if (!res.ok) {
        let msg = "Ошибка генерации PDF";
        try {
          const err = await res.json();
          msg = err.detail || msg;
        } catch {
          /* ignore */
        }
        setError(typeof msg === "string" ? msg : "Ошибка генерации PDF");
        return;
      }

      setPdfStatus("Скачиваем файл…");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `homework_${lesson?.student_name || "student"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setSuccess("PDF готов и скачан.");
    } catch {
      setError("Не удалось связаться с сервером. Проверьте интернет или войдите снова.");
    } finally {
      window.clearInterval(statusTimer);
      setPdfLoading(false);
      setPdfStatus("");
    }
  };

  const togglePaid = async () => {
    if (!lesson) return;
    setTogglingPaid(true);
    setError("");
    try {
      await api.lessons.togglePaid(lessonId, !lesson.is_paid);
      setSuccess(lesson.is_paid ? "Отмечено как не оплачено" : "Оплата отмечена");
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setTogglingPaid(false);
    }
  };

  const downloadSubmission = async (submissionId: number, filename: string) => {
    if (!homeworkId) return;
    const res = await authFetch(api.homework.submissionFileUrl(homeworkId, submissionId));
    if (!res.ok) {
      setError("Не удалось скачать файл");
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const reviewSubmission = async (
    submissionId: number,
    status: "reviewed" | "needs_revision"
  ) => {
    if (!homeworkId) return;
    setReviewingId(submissionId);
    setError("");
    try {
      await api.homework.reviewSubmission(homeworkId, submissionId, {
        status,
        tutor_comment: reviewComments[submissionId] || "",
      });
      setSuccess(status === "reviewed" ? "Отмечено как проверено" : "Отправлено на доработку");
      loadSubmissions(homeworkId);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка проверки");
    } finally {
      setReviewingId(null);
    }
  };

  if (loading && !lesson) return <LoadingSpinner label="Загрузка урока..." />;
  if (loadError && !lesson) return <LoadError message={loadError} onRetry={load} />;

  const editData: LessonFormData | null = lesson
    ? {
        id: lesson.id,
        student_id: lesson.student_id,
        student_name: lesson.student_name,
        lesson_date: lesson.lesson_date.slice(0, 10),
        lesson_time: lesson.lesson_time || "10:00",
        duration_minutes: lesson.duration_minutes,
        payment_amount: lesson.payment_amount,
        is_paid: lesson.is_paid,
        notes: lesson.notes || "",
        meeting_url: lesson.meeting_url || "",
      }
    : null;

  return (
    <div className="max-w-4xl">
      <Link href="/lessons" className="text-sm text-brand-blue hover:underline">← Занятия</Link>

      <div className="mt-4 p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="rc-page-title">{lesson?.student_name}</h1>
          <p className="text-slate-600 mt-1">
            {lesson &&
              new Date(lesson.lesson_date).toLocaleDateString("ru-RU", {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}{" "}
            в <span className="font-semibold">{formatLessonTime(lesson?.lesson_time)}</span>
            {" · "}
            {lesson?.duration_minutes} мин
          </p>
          {lesson?.meeting_url && (
            <a
              href={lesson.meeting_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-2 text-sm font-medium text-brand-blue hover:underline"
            >
              Ссылка на урок →
            </a>
          )}
          <p className="mt-2 text-sm flex flex-wrap items-center gap-2">
            {lesson?.is_paid ? (
              <span className="text-brand-green font-medium">
                Оплачено · {formatMoney(lesson.payment_amount)}
              </span>
            ) : (
              <span className="text-amber-600 font-medium">
                Не оплачено · {lesson?.payment_amount != null ? formatMoney(lesson.payment_amount) : "—"}
              </span>
            )}
            <button
              type="button"
              onClick={togglePaid}
              disabled={togglingPaid}
              className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                lesson?.is_paid
                  ? "border-slate-200 text-slate-600 hover:bg-slate-50"
                  : "border-brand-green text-brand-green hover:bg-emerald-50"
              } disabled:opacity-50`}
            >
              {togglingPaid ? "…" : lesson?.is_paid ? "Снять оплату" : "Отметить оплату"}
            </button>
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          {lesson?.board_id ? (
            <Link
              href={`/boards/${lesson.board_id}?lesson=${lessonId}`}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 text-white font-medium"
            >
              Виртуальная доска →
            </Link>
          ) : null}
          <button
            type="button"
            onClick={() => {
              const el = document.getElementById("after-lesson");
              el?.scrollIntoView({ behavior: "smooth", block: "start" });
              if (!isConducted) setIsConducted(true);
            }}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-brand-green text-white text-sm font-medium"
          >
            Если занятие прошло — сюда →
          </button>
          <button
            type="button"
            onClick={() => setShowEdit(true)}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl border border-brand-blue text-brand-blue font-medium hover:bg-brand-mist"
          >
            <PencilIcon className="w-5 h-5" />
            Редактировать
          </button>
        </div>
      </div>

      {error && <div className="mt-4"><Alert message={error} onClose={() => setError("")} /></div>}
      {success && <div className="mt-4"><Alert type="success" message={success} onClose={() => setSuccess("")} /></div>}
      {trialFollowup && (
        <div className="mt-4">
          <TrialFollowupBanner message={trialFollowup} />
        </div>
      )}

      {showEdit && editData && (
        <LessonFormModal
          mode="edit"
          lesson={editData}
          onClose={() => setShowEdit(false)}
          onSaved={() => {
            setShowEdit(false);
            load();
          }}
        />
      )}

      <section id="after-lesson" className="mt-8 p-6 rounded-2xl bg-white border shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-lg">После занятия</h2>
            <p className="text-sm text-slate-500 mt-1">
              Отметьте проведение и заполните чек-лист — так нейросеть точнее соберёт ДЗ
            </p>
          </div>
          {isConducted ? (
            <span className="px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm font-medium">
              Занятие проведено
            </span>
          ) : (
            <button
              type="button"
              onClick={() => {
                setIsConducted(true);
                setSuccess("");
                setError("");
              }}
              className="px-5 py-2.5 rounded-xl bg-brand-green text-white text-sm font-medium"
            >
              Занятие проведено
            </button>
          )}
        </div>

        {isConducted && (
          <>
            <h3 className="mt-6 font-medium text-slate-800">Блок 1. Темы занятия *</h3>
            <p className="text-sm text-slate-500">Какую тему (темы) проходили?</p>
          </>
        )}

        {!isConducted && (
          <p className="mt-4 text-sm text-amber-700 bg-amber-50 px-4 py-3 rounded-xl">
            Нажмите «Занятие проведено», чтобы открыть форму для генерации домашки.
          </p>
        )}
        {isConducted && (
        <>
        <div className="mt-4 space-y-4">
          {rows.map((row, idx) => (
            <div key={idx} className="grid gap-3 sm:grid-cols-12 items-start p-4 rounded-xl bg-slate-50">
              <input
                placeholder="Тема"
                value={row.topic}
                onChange={(e) => {
                  const n = [...rows];
                  n[idx].topic = e.target.value;
                  setRows(n);
                }}
                className="sm:col-span-4 px-3 py-2 rounded-lg border text-sm"
              />
              <select
                value={row.work_type}
                onChange={(e) => {
                  const n = [...rows];
                  n[idx].work_type = e.target.value;
                  setRows(n);
                }}
                className="sm:col-span-2 px-3 py-2 rounded-lg border text-sm"
              >
                <option value="theory">Теория</option>
                <option value="practice">Практика</option>
                <option value="test">Тест</option>
              </select>
              <select
                value={row.difficulty}
                onChange={(e) => {
                  const n = [...rows];
                  n[idx].difficulty = e.target.value;
                  setRows(n);
                }}
                className="sm:col-span-3 px-3 py-2 rounded-lg border text-sm"
              >
                <option value="basic">Базовая</option>
                <option value="medium">Средняя</option>
                <option value="advanced">Продвинутая</option>
              </select>
              <button
                type="button"
                onClick={() => setRows(rows.filter((_, i) => i !== idx))}
                className="sm:col-span-3 p-2 text-red-500 hover:bg-red-50 rounded-lg justify-self-end"
              >
                <TrashIcon className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>

        <div className="mt-8 pt-6 border-t">
          <LessonHomeworkForm
            prefs={prefs}
            onChange={setPrefs}
            showOptional={showOptional}
          />
          <button
            type="button"
            onClick={() => setShowOptional(!showOptional)}
            className="mt-4 text-sm text-brand-blue hover:underline"
          >
            {showOptional ? "Скрыть дополнительные настройки" : "Показать все настройки (объём, типы, пожелания…)"}
          </button>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setRows([...rows, emptyRow()])}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border text-sm"
          >
            <PlusIcon className="w-4 h-4" /> Тема
          </button>
          <button
            onClick={() => saveLessonReport(true)}
            disabled={saving}
            className="px-4 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium disabled:opacity-60"
          >
            {saving ? "Сохранение..." : "Сохранить"}
          </button>
          <button
            onClick={generate}
            disabled={generating || saving}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-brand-green text-white text-sm font-medium disabled:opacity-60"
          >
            <SparklesIcon className={`w-5 h-5 ${generating ? "animate-pulse" : ""}`} />
            {generating ? "Генерация…" : "Сгенерировать ДЗ"}
          </button>
        </div>
        {generating && (
          <p className="mt-3 text-sm text-slate-500">
            Запрос принят. Сейчас запустим генерацию…
          </p>
        )}
        {jobId && (jobStatus === "queued" || jobStatus === "running") && (
          <p className="mt-3 text-sm text-slate-500">
            {jobStatus === "queued" ? "В очереди…" : "Генерируем…"} {jobHint}
          </p>
        )}

        <HomeworkTemplatesPanel
          lessonId={lessonId}
          hasHomework={!!homeworkId}
          onApplied={load}
          onPrefsLoaded={setPrefs}
          onRowsLoaded={(r) => setRows(r.length ? r : [emptyRow()])}
        />
        <VoiceBriefButton
          lessonId={lessonId}
          onStarted={(jobId, brief) => {
            setSuccess(`Бриф сохранён: «${brief.slice(0, 80)}${brief.length > 80 ? "…" : ""}»`);
            if (jobId) {
              setJobId(jobId);
              setJobStatus("queued");
              setJobHint("Генерируем ДЗ из голосового брифа…");
              setGenerating(true);
              window.localStorage.setItem(`repetcrm:hw_job:${lessonId}`, jobId);
            }
            load();
          }}
          onError={(msg) => setError(msg)}
        />
        </>
        )}
      </section>

      {homeworkHtml && (
        <section className="mt-8 p-6 rounded-2xl bg-white border shadow-sm">
          <div className="flex flex-wrap justify-between items-center gap-4">
            <h2 className="font-semibold text-lg">Домашнее задание</h2>
            <div className="flex flex-wrap gap-2">
              {!editMode && (
                <>
                  <button
                    onClick={() => setHomeworkView("latex")}
                    className={`px-4 py-2 rounded-xl border text-sm ${
                      homeworkView === "latex" ? "bg-brand-blue text-white border-brand-blue" : ""
                    }`}
                  >
                    Код LaTeX
                  </button>
                  <button
                    onClick={() => setHomeworkView("preview")}
                    className={`px-4 py-2 rounded-xl border text-sm ${
                      homeworkView === "preview" ? "bg-brand-blue text-white border-brand-blue" : ""
                    }`}
                  >
                    Задания
                  </button>
                </>
              )}
              <button
                onClick={() => setEditMode(!editMode)}
                className="px-4 py-2 rounded-xl border text-sm"
              >
                {editMode ? "Просмотр" : "Редактировать"}
              </button>
              {editMode && (
                <button
                  onClick={saveHomework}
                  disabled={saving}
                  className="px-4 py-2 rounded-xl bg-brand-blue text-white text-sm"
                >
                  Сохранить
                </button>
              )}
              <button
                onClick={downloadLatex}
                className="px-4 py-2 rounded-xl border text-sm hover:bg-slate-50"
              >
                .tex
              </button>
              <button
                onClick={downloadPython}
                className="px-4 py-2 rounded-xl border text-sm hover:bg-slate-50"
              >
                Python
              </button>
              <button
                onClick={downloadPdf}
                disabled={pdfLoading}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-green text-white text-sm disabled:opacity-70 disabled:cursor-wait"
              >
                {pdfLoading ? (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <ArrowDownTrayIcon className="w-4 h-4" />
                )}
                {pdfLoading ? "PDF…" : "PDF"}
              </button>
            </div>
          </div>
          {homeworkId && (
            <div className="mt-4 flex flex-wrap items-end gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">
                  Срок сдачи для ученика
                </label>
                <input
                  type="date"
                  value={homeworkDueDate}
                  onChange={(e) => setHomeworkDueDate(e.target.value)}
                  className="px-3 py-2 rounded-xl border border-slate-200 text-sm bg-white"
                />
              </div>
              <button
                type="button"
                onClick={saveDueDate}
                disabled={saving}
                className="px-4 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium disabled:opacity-60"
              >
                Сохранить срок
              </button>
            </div>
          )}
          {pdfLoading && (
            <div
              className="mt-4 rounded-xl border border-brand-green/25 bg-emerald-50/80 p-4"
              role="status"
              aria-live="polite"
            >
              <div className="flex items-center gap-3">
                <span className="w-5 h-5 shrink-0 border-2 border-brand-green border-t-transparent rounded-full animate-spin" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-brand-green">{pdfStatus}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Качественный PDF с формулами — обычно 20–55 секунд.
                  </p>
                </div>
              </div>
              <div className="mt-3 h-1.5 w-full rounded-full bg-emerald-100 overflow-hidden">
                <div className="pdf-progress-bar h-full rounded-full bg-brand-green" />
              </div>
            </div>
          )}
          {editMode ? (
            <textarea
              value={homeworkHtml}
              onChange={(e) => setHomeworkHtml(e.target.value)}
              className="mt-4 w-full h-80 px-4 py-3 rounded-xl border font-mono text-sm leading-relaxed"
              spellCheck={false}
            />
          ) : homeworkView === "latex" ? (
            <pre className="mt-4 p-6 rounded-xl bg-slate-900 text-slate-100 text-sm overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed max-h-[32rem] overflow-y-auto">
              {homeworkHtml}
            </pre>
          ) : (
            <div
              className="mt-4 p-6 rounded-xl bg-slate-50 prose prose-sm max-w-none lesson-homework"
              dangerouslySetInnerHTML={{
                __html: sanitizeHomeworkHtml(homeworkDisplayHtml || homeworkHtml),
              }}
            />
          )}
          {submissions.length > 0 && (
            <div className="mt-6 pt-6 border-t">
              <h3 className="font-medium text-slate-800 mb-3">Ответы ученика</h3>
              <ul className="space-y-2">
                {submissions.map((s) => (
                  <li
                    key={s.id}
                    className="p-3 rounded-xl bg-slate-50 text-sm space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-medium truncate">{s.original_filename}</p>
                        <p className="text-xs text-slate-500">
                          {new Date(s.submitted_at).toLocaleString("ru-RU")}
                          {s.comment ? ` · ${s.comment}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-medium px-2 py-1 rounded-lg ${
                            s.status === "reviewed"
                              ? "bg-emerald-100 text-emerald-800"
                              : s.status === "needs_revision"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-slate-200 text-slate-700"
                          }`}
                        >
                          {submissionStatusLabel[s.status] || s.status}
                        </span>
                        <button
                          type="button"
                          onClick={() => downloadSubmission(s.id, s.original_filename)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border text-sm hover:bg-white"
                        >
                          <ArrowDownTrayIcon className="w-4 h-4" />
                          Скачать
                        </button>
                      </div>
                    </div>
                    {s.tutor_comment && (
                      <p className="text-xs text-slate-600 bg-white rounded-lg p-2 border">
                        Комментарий: {s.tutor_comment}
                      </p>
                    )}
                    {s.ai_review_status === "done" && s.ai_verdict && (
                      <div
                        className={`text-xs rounded-lg p-3 border ${
                          s.ai_verdict === "correct"
                            ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                            : s.ai_verdict === "partially_correct"
                              ? "bg-amber-50 border-amber-200 text-amber-900"
                              : s.ai_verdict === "incorrect"
                                ? "bg-red-50 border-red-200 text-red-900"
                                : "bg-slate-50 border-slate-200 text-slate-700"
                        }`}
                      >
                        <p className="font-medium">
                          AI: {aiVerdictLabel[s.ai_verdict] || s.ai_verdict}
                          {s.ai_verdict !== "unclear" && s.ai_score != null ? ` · ${s.ai_score}%` : ""}
                        </p>
                        {s.ai_feedback && <p className="mt-1">{s.ai_feedback}</p>}
                      </div>
                    )}
                    {(s.ai_review_status === "pending" || s.ai_review_status === "running") && (
                      <p className="text-xs text-slate-500">AI проверяет решение…</p>
                    )}
                    {s.status === "submitted" && (
                      <div className="flex flex-col sm:flex-row gap-2 pt-1">
                        <input
                          type="text"
                          placeholder="Комментарий родителю/ученику (необязательно)"
                          value={reviewComments[s.id] || ""}
                          onChange={(e) =>
                            setReviewComments((prev) => ({ ...prev, [s.id]: e.target.value }))
                          }
                          className="flex-1 px-3 py-2 rounded-lg border text-sm"
                        />
                        <button
                          type="button"
                          disabled={reviewingId === s.id}
                          onClick={() => reviewSubmission(s.id, "reviewed")}
                          className="px-3 py-2 rounded-lg bg-brand-green text-white text-sm font-medium"
                        >
                          Проверено
                        </button>
                        <button
                          type="button"
                          disabled={reviewingId === s.id}
                          onClick={() => reviewSubmission(s.id, "needs_revision")}
                          className="px-3 py-2 rounded-lg border text-sm font-medium"
                        >
                          На доработку
                        </button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* Mobile sticky actions */}
      <div className="fixed bottom-0 left-0 right-0 z-30 lg:hidden border-t bg-white/95 backdrop-blur px-4 py-3 flex gap-2 safe-area-pb">
        {lesson?.board_id ? (
          <Link
            href={`/boards/${lesson.board_id}?lesson=${lessonId}`}
            className="flex-1 text-center py-2.5 rounded-xl bg-slate-900 text-white text-sm font-medium"
          >
            Доска
          </Link>
        ) : null}
        <button
          type="button"
          onClick={togglePaid}
          disabled={togglingPaid}
          className={`flex-1 py-2.5 rounded-xl text-sm font-medium border ${
            lesson?.is_paid
              ? "border-slate-200 text-slate-700"
              : "border-brand-green bg-brand-green text-white"
          }`}
        >
          {lesson?.is_paid ? "Оплачено ✓" : "Оплату ✓"}
        </button>
        <button
          type="button"
          onClick={() => document.getElementById("after-lesson")?.scrollIntoView({ behavior: "smooth" })}
          className="flex-1 py-2.5 rounded-xl bg-brand-blue text-white text-sm font-medium"
        >
          ДЗ
        </button>
      </div>
      <div className="h-20 lg:hidden" aria-hidden />
    </div>
  );
}
