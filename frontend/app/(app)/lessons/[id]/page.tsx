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
import { getToken } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import Alert from "@/components/Alert";
import LessonHomeworkForm from "@/components/LessonHomeworkForm";
import { defaultHomeworkPrefs, HomeworkPrefs } from "@/lib/homeworkPrefs";
import { formatMoney } from "@/lib/currency";

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
  checklist_items: Array<ChecklistRow & { id?: number }>;
  homework?: { id: number; homework_text: string };
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
  const [homeworkView, setHomeworkView] = useState<"latex" | "preview">("preview");
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfStatus, setPdfStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showEdit, setShowEdit] = useState(false);
  const [isConducted, setIsConducted] = useState(false);
  const [prefs, setPrefs] = useState<HomeworkPrefs>(defaultHomeworkPrefs());
  const [showOptional, setShowOptional] = useState(true);

  const load = useCallback(() => {
    const token = getToken();
    if (!token) return;
    api.lessons.get<Lesson>(token, lessonId).then((l) => {
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
      setPrefs(l.homework_prefs ? { ...defaultHomeworkPrefs(), ...l.homework_prefs } : defaultHomeworkPrefs());
      if (l.homework) {
        setHomeworkHtml(l.homework.homework_text);
        setHomeworkId(l.homework.id);
        api.homework
          .previewHtml(token, l.homework.id)
          .then((p) => setHomeworkDisplayHtml(p.html))
          .catch(() => setHomeworkDisplayHtml(l.homework!.homework_text));
      } else {
        setHomeworkDisplayHtml("");
      }
      setLoading(false);
    });
  }, [lessonId]);

  useEffect(() => load(), [load]);

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
    const token = getToken();
    if (!token) return false;
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
      await api.lessons.saveLessonReport(token, lessonId, {
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
    const token = getToken();
    if (!token) return;
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
      const hw = await api.lessons.generateHomework<{
        id: number;
        homework_text: string;
        generation_source?: string;
        generation_hint?: string;
        configured_provider?: string;
        configured_model?: string;
      }>(token, lessonId);
      setHomeworkHtml(hw.homework_text);
      setHomeworkId(hw.id);
      setHomeworkView("preview");
      if (hw.id) {
        api.homework
          .previewHtml(token, hw.id)
          .then((p) => setHomeworkDisplayHtml(p.html))
          .catch(() => setHomeworkDisplayHtml(hw.homework_text));
      }
      // Keep UX simple: no internal provider/debug details in UI.
      setSuccess(hw.generation_hint || "Домашнее задание готово.");
      load();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка генерации";
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  const saveHomework = async () => {
    if (!homeworkId) return;
    const token = getToken();
    if (!token) return;
    setSaving(true);
    try {
      await api.homework.update(token, homeworkId, homeworkHtml);
      setEditMode(false);
      setSuccess("ДЗ сохранено");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setSaving(false);
    }
  };

  const downloadPython = async () => {
    if (!homeworkId) return;
    const token = getToken();
    const res = await fetch(api.homework.pythonScriptUrl(homeworkId), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
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
    const token = getToken();
    const res = await fetch(api.homework.latexUrl(homeworkId), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
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
    const token = getToken();
    if (!token) return;
    setError("");
    setPdfLoading(true);
    setPdfStatus("Подготавливаем домашнее задание…");

    const statusSteps = [
      "Компилируем формулы (LaTeX)…",
      "Собираем PDF…",
      "Почти готово…",
    ];
    let step = 0;
    const statusTimer = window.setInterval(() => {
      setPdfStatus(statusSteps[Math.min(step, statusSteps.length - 1)]);
      step += 1;
    }, 9000);

    try {
      const res = await fetch(api.homework.pdfUrl(homeworkId), {
        headers: { Authorization: `Bearer ${token}` },
      });
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
      setError(
        "Не удалось связаться с сервером. Запущен ли бэкенд на порту 8000?"
      );
    } finally {
      window.clearInterval(statusTimer);
      setPdfLoading(false);
      setPdfStatus("");
    }
  };

  if (loading) return <LoadingSpinner label="Загрузка урока..." />;

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
      }
    : null;

  return (
    <div className="max-w-4xl">
      <Link href="/lessons" className="text-sm text-brand-blue hover:underline">← Занятия</Link>

      <div className="mt-4 p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-brand-blue">{lesson?.student_name}</h1>
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
          <p className="mt-2 text-sm">
            {lesson?.is_paid ? (
              <span className="text-brand-green font-medium">
                Оплачено · {formatMoney(lesson.payment_amount)}
              </span>
            ) : (
              <span className="text-amber-600 font-medium">
                Не оплачено · {lesson?.payment_amount != null ? formatMoney(lesson.payment_amount) : "—"}
              </span>
            )}
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
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl border border-brand-blue text-brand-blue font-medium hover:bg-blue-50"
          >
            <PencilIcon className="w-5 h-5" />
            Редактировать
          </button>
        </div>
      </div>

      {error && <div className="mt-4"><Alert message={error} onClose={() => setError("")} /></div>}
      {success && <div className="mt-4"><Alert type="success" message={success} onClose={() => setSuccess("")} /></div>}

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
            OpenRouter: обычно 10–40 сек. Не закрывайте страницу.
          </p>
        )}
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
                    Обычно 20–40 секунд (LaTeX и формулы). Не закрывайте страницу.
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
              dangerouslySetInnerHTML={{ __html: homeworkDisplayHtml || homeworkHtml }}
            />
          )}
        </section>
      )}
    </div>
  );
}
