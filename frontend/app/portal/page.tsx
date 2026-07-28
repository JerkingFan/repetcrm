"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { formatLessonTime } from "@/lib/calendar";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";

function PortalContent() {
  const params = useSearchParams();
  const tokenFromUrl = params.get("token") || "";

  const [student, setStudent] = useState<Awaited<ReturnType<typeof api.portal.me>> | null>(null);
  const [lessons, setLessons] = useState<Awaited<ReturnType<typeof api.portal.lessons>>>([]);
  const [homework, setHomework] = useState<Awaited<ReturnType<typeof api.portal.homework>>>([]);
  const [selectedHw, setSelectedHw] = useState<number | null>(null);
  const [hwDetail, setHwDetail] = useState<Awaited<ReturnType<typeof api.portal.homeworkDetail>> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [comment, setComment] = useState("");
  const [success, setSuccess] = useState("");
  const [payAmount, setPayAmount] = useState("40");

  const loadData = async () => {
    const me = await api.portal.me();
    setStudent(me);
    const [ls, hw] = await Promise.all([api.portal.lessons(), api.portal.homework()]);
    setLessons(ls);
    setHomework(hw);
  };

  useEffect(() => {
    (async () => {
      try {
        if (tokenFromUrl) {
          await api.portal.login(tokenFromUrl);
        }
        await loadData();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Не удалось войти");
      } finally {
        setLoading(false);
      }
    })();
  }, [tokenFromUrl]);

  useEffect(() => {
    if (!selectedHw) {
      setHwDetail(null);
      return;
    }
    api.portal.homeworkDetail(selectedHw).then(setHwDetail).catch(() => setHwDetail(null));
  }, [selectedHw]);

  useEffect(() => {
    if (!selectedHw || !hwDetail) return;
    const needsPoll = hwDetail.submissions.some(
      (s) => s.ai_review_status === "pending" || s.ai_review_status === "running"
    );
    if (!needsPoll) return;
    const timer = setInterval(() => {
      api.portal.homeworkDetail(selectedHw).then(setHwDetail).catch(() => {});
    }, 3000);
    return () => clearInterval(timer);
  }, [selectedHw, hwDetail]);

  const aiVerdictLabel: Record<string, string> = {
    correct: "Верно ✓",
    partially_correct: "Частично верно",
    incorrect: "Есть ошибки",
    unclear: "Не удалось оценить",
  };

  const aiVerdictStyle: Record<string, string> = {
    correct: "bg-emerald-50 border-emerald-200 text-emerald-900",
    partially_correct: "bg-amber-50 border-amber-200 text-amber-900",
    incorrect: "bg-red-50 border-red-200 text-red-900",
    unclear: "bg-slate-50 border-slate-200 text-slate-700",
  };

  const latestSubmission = hwDetail?.submissions[0];

  const submitFile = async (file: File) => {
    if (!selectedHw) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      await api.portal.submitHomework(selectedHw, file, comment);
      setSuccess("Ответ отправлен! AI проверяет решение…");
      setComment("");
      await loadData();
      if (selectedHw) setHwDetail(await api.portal.homeworkDetail(selectedHw));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка загрузки");
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <LoadingSpinner label="Вход в кабинет..." />;

  if (!student) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="max-w-md text-center space-y-4">
          <h1 className="text-2xl font-bold text-brand-blue">Кабинет ученика</h1>
          {error ? <Alert message={error} /> : <p className="text-slate-500">Нужна ссылка от репетитора</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-3xl mx-auto flex justify-between items-start">
          <div>
            <h1 className="text-xl font-bold text-brand-blue">Привет, {student.name}!</h1>
            <p className="text-sm text-slate-500">
              {student.subject} · {student.grade} · Репетитор: {student.tutor_name}
            </p>
            {student.balance > 0 && (
              <p className="text-sm text-emerald-700 mt-1">Баланс: {student.balance} Br</p>
            )}
          </div>
          <a
            href={api.portal.calendarIcsUrl()}
            className="text-sm text-brand-blue hover:underline shrink-0"
          >
            Календарь (.ics)
          </a>
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-8">
        {error && <Alert message={error} onClose={() => setError("")} />}
        {success && <Alert type="success" message={success} />}

        <section className="bg-white rounded-2xl border p-6 shadow-sm">
          <h2 className="font-semibold text-brand-blue">Пополнить баланс</h2>
          <p className="text-sm text-slate-500 mt-1">
            Текущий баланс: <strong>{student.balance} Br</strong>
          </p>
          <div className="mt-4 flex flex-wrap gap-2 items-end">
            <input
              type="number"
              min={1}
              value={payAmount}
              onChange={(e) => setPayAmount(e.target.value)}
              className="w-28 px-3 py-2 rounded-xl border text-sm"
            />
            <button
              type="button"
              onClick={async () => {
                const amount = Number(payAmount);
                if (amount <= 0) return;
                try {
                  const r = await api.portal.createPaymentIntent(amount, "card");
                  if (r.payment_url) window.location.href = r.payment_url;
                } catch (e) {
                  setError(e instanceof ApiError ? e.message : "Ошибка");
                }
              }}
              className="px-4 py-2 rounded-xl bg-brand-green text-white text-sm font-medium"
            >
              Оплатить картой
            </button>
            <button
              type="button"
              onClick={async () => {
                const amount = Number(payAmount);
                if (amount <= 0) return;
                try {
                  const r = await api.portal.createPaymentIntent(amount, "erip");
                  if (r.payment_url) window.location.href = r.payment_url;
                } catch (e) {
                  setError(e instanceof ApiError ? e.message : "Ошибка");
                }
              }}
              className="px-4 py-2 rounded-xl border text-sm font-medium"
            >
              Через ЕРИП
            </button>
          </div>
        </section>

        <section className="bg-white rounded-2xl border p-6 shadow-sm">
          <h2 className="font-semibold text-brand-blue">Расписание</h2>
          {lessons.length === 0 ? (
            <p className="text-sm text-slate-500 mt-3">Ближайших занятий нет</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {lessons.map((l) => (
                <li key={l.id} className="flex justify-between text-sm border-b border-slate-100 pb-2">
                  <span>
                    {new Date(l.lesson_date).toLocaleDateString("ru-RU")} · {formatLessonTime(l.lesson_time)}
                  </span>
                  <span className="text-slate-500">{l.duration_minutes} мин</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bg-white rounded-2xl border p-6 shadow-sm">
          <h2 className="font-semibold text-brand-blue">Домашние задания</h2>
          {homework.length === 0 ? (
            <p className="text-sm text-slate-500 mt-3">Пока нет ДЗ</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {homework.map((h) => (
                <li key={h.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedHw(h.id)}
                    className={`w-full text-left p-3 rounded-xl border ${
                      selectedHw === h.id ? "border-brand-green bg-emerald-50" : "border-slate-100 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex justify-between gap-2">
                      <span className="font-medium text-sm">
                        {new Date(h.lesson_date).toLocaleDateString("ru-RU")}
                      </span>
                      {h.has_submission && (
                        <span className="text-xs text-brand-green font-medium">
                          {h.submission_status === "reviewed"
                            ? "Проверено ✓"
                            : h.submission_status === "needs_revision"
                              ? "Доработать"
                              : h.submission_status === "submitted"
                                ? "На проверке"
                                : "Сдано ✓"}
                        </span>
                      )}
                    </div>
                    {h.preview && <p className="text-xs text-slate-500 mt-1 line-clamp-2">{h.preview}</p>}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {hwDetail && (
            <div className="mt-6 pt-6 border-t space-y-4">
              <div
                className="prose prose-sm max-w-none text-slate-700 max-h-48 overflow-y-auto p-3 bg-slate-50 rounded-xl"
                dangerouslySetInnerHTML={{
                  __html: hwDetail.preview_html || hwDetail.homework_text,
                }}
              />
              <div>
                <label className="block text-sm font-medium mb-1">Сдать ответ (PDF или фото)</label>
                <input
                  type="file"
                  accept=".pdf,image/jpeg,image/png,image/webp"
                  disabled={uploading}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) submitFile(f);
                    e.target.value = "";
                  }}
                  className="text-sm w-full"
                />
              </div>
              <input
                type="text"
                placeholder="Комментарий (необязательно)"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border text-sm"
              />
              {hwDetail.submissions.length > 0 && (
                <p className="text-xs text-slate-500">
                  Отправлено: {hwDetail.submissions.map((s) => s.original_filename).join(", ")}
                </p>
              )}
              {latestSubmission &&
                (latestSubmission.ai_review_status === "pending" ||
                  latestSubmission.ai_review_status === "running") && (
                  <div className="p-4 rounded-xl border border-blue-200 bg-blue-50 text-sm text-blue-900">
                    AI проверяет ваше решение… Обычно это занимает 10–30 секунд.
                  </div>
                )}
              {latestSubmission?.ai_review_status === "done" && latestSubmission.ai_verdict && (
                <div
                  className={`p-4 rounded-xl border text-sm ${
                    aiVerdictStyle[latestSubmission.ai_verdict] || aiVerdictStyle.unclear
                  }`}
                >
                  <p className="font-semibold">
                    {aiVerdictLabel[latestSubmission.ai_verdict] || latestSubmission.ai_verdict}
                    {latestSubmission.ai_score != null ? ` · ${latestSubmission.ai_score}%` : ""}
                  </p>
                  {latestSubmission.ai_feedback && (
                    <p className="mt-2 leading-relaxed">{latestSubmission.ai_feedback}</p>
                  )}
                  <p className="mt-2 text-xs opacity-80">
                    Это предварительная оценка AI. Репетитор может скорректировать результат.
                  </p>
                </div>
              )}
              {latestSubmission?.ai_review_status === "skipped" && latestSubmission.ai_feedback && (
                <p className="text-xs text-slate-500">{latestSubmission.ai_feedback}</p>
              )}
              {latestSubmission?.ai_review_status === "error" && (
                <p className="text-xs text-amber-700">
                  Автопроверка не сработала — репетитор проверит вручную.
                </p>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default function PortalPage() {
  return (
    <Suspense fallback={<LoadingSpinner label="Загрузка..." />}>
      <PortalContent />
    </Suspense>
  );
}
