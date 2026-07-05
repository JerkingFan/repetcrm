"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { formatLessonTime } from "@/lib/calendar";
import { formatMoney } from "@/lib/currency";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";

function ParentPortalContent() {
  const params = useSearchParams();
  const tokenFromUrl = params.get("token") || "";

  const [info, setInfo] = useState<Awaited<ReturnType<typeof api.parentPortal.me>> | null>(null);
  const [lessons, setLessons] = useState<Awaited<ReturnType<typeof api.parentPortal.lessons>>>([]);
  const [packages, setPackages] = useState<Awaited<ReturnType<typeof api.parentPortal.packages>>>([]);
  const [homeworkStatus, setHomeworkStatus] = useState<
    Awaited<ReturnType<typeof api.parentPortal.homeworkStatus>>
  >([]);
  const [reportMonth, setReportMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
  const [report, setReport] = useState<Awaited<ReturnType<typeof api.parentPortal.report>> | null>(
    null
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [payAmount, setPayAmount] = useState("80");
  const [payNote, setPayNote] = useState("");
  const [payFile, setPayFile] = useState<File | null>(null);
  const [paymentDetails, setPaymentDetails] = useState<
    Awaited<ReturnType<typeof api.parentPortal.paymentDetails>> | null
  >(null);
  const [receipts, setReceipts] = useState<
    Awaited<ReturnType<typeof api.parentPortal.listReceipts>>
  >([]);
  const [submittingPay, setSubmittingPay] = useState(false);
  const [paySuccess, setPaySuccess] = useState("");

  const loadData = async () => {
    const me = await api.parentPortal.me();
    setInfo(me);
    const [ls, pkgs, hw] = await Promise.all([
      api.parentPortal.lessons(),
      api.parentPortal.packages(),
      api.parentPortal.homeworkStatus(),
    ]);
    setLessons(ls);
    setPackages(pkgs);
    setHomeworkStatus(hw);
    const [pd, rc] = await Promise.all([
      api.parentPortal.paymentDetails(),
      api.parentPortal.listReceipts(),
    ]);
    setPaymentDetails(pd);
    setReceipts(rc);
  };

  useEffect(() => {
    if (!info) return;
    api.parentPortal.report(reportMonth).then(setReport).catch(() => setReport(null));
  }, [info, reportMonth]);

  useEffect(() => {
    (async () => {
      try {
        if (tokenFromUrl) {
          await api.parentPortal.login(tokenFromUrl);
        }
        await loadData();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Не удалось войти");
      } finally {
        setLoading(false);
      }
    })();
  }, [tokenFromUrl]);

  if (loading) return <LoadingSpinner label="Вход в кабинет родителя..." />;

  if (!info) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="max-w-md text-center space-y-4">
          <h1 className="text-2xl font-bold text-brand-blue">Кабинет родителя</h1>
          {error ? <Alert message={error} /> : <p className="text-slate-500">Нужна ссылка от репетитора</p>}
        </div>
      </div>
    );
  }

  const activePackage = packages.find((p) => p.is_active && p.lessons_remaining > 0);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-3xl mx-auto flex justify-between items-start gap-4">
          <div>
            <h1 className="text-xl font-bold text-brand-blue">
              {info.parent_name ? `Здравствуйте, ${info.parent_name}` : "Кабинет родителя"}
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Ученик: <strong>{info.student_name}</strong> · {info.subject} · {info.grade}
            </p>
            <p className="text-sm text-slate-500">Репетитор: {info.tutor_name}</p>
            <p className="text-sm text-emerald-700 mt-2 font-medium">
              Баланс: {formatMoney(info.balance)}
            </p>
            {activePackage && (
              <p className="text-xs text-slate-500 mt-1">
                Абонемент «{activePackage.name}»: осталось {activePackage.lessons_remaining} из{" "}
                {activePackage.lessons_total} занятий
              </p>
            )}
          </div>
          <a
            href={api.parentPortal.calendarIcsUrl()}
            className="text-sm text-brand-blue hover:underline shrink-0"
          >
            Календарь (.ics)
          </a>
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-8">
        {error && <Alert message={error} onClose={() => setError("")} />}

        <section className="bg-white rounded-2xl border p-6 shadow-sm space-y-4">
          <h2 className="font-semibold text-brand-blue">Оплата занятий</h2>
          <p className="text-sm text-slate-500">
            Переведите сумму по реквизитам репетитора и прикрепите чек (фото или PDF). После
            проверки средства зачислятся на баланс {info.student_name}.
          </p>

          {paymentDetails?.has_requisites ? (
            <>
              <pre className="text-sm bg-slate-50 border rounded-xl p-4 whitespace-pre-wrap font-sans">
                {paymentDetails.payment_details}
              </pre>
              <div className="flex flex-wrap gap-3 items-end">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">Сумма (Br)</label>
                  <input
                    type="number"
                    min={1}
                    value={payAmount}
                    onChange={(e) => setPayAmount(e.target.value)}
                    className="w-28 px-3 py-2 rounded-xl border text-sm"
                  />
                </div>
                <div className="flex-1 min-w-[200px]">
                  <label className="block text-xs text-slate-500 mb-1">Чек (PDF, JPG, PNG)</label>
                  <input
                    type="file"
                    accept=".pdf,image/jpeg,image/png,image/webp"
                    onChange={(e) => setPayFile(e.target.files?.[0] || null)}
                    className="block w-full text-sm"
                  />
                </div>
              </div>
              <input
                type="text"
                value={payNote}
                onChange={(e) => setPayNote(e.target.value)}
                placeholder="Комментарий (необязательно)"
                className="w-full px-3 py-2 rounded-xl border text-sm"
              />
              {paySuccess && <Alert type="success" message={paySuccess} />}
              <button
                type="button"
                disabled={submittingPay || !payFile}
                onClick={async () => {
                  const amount = Number(payAmount);
                  if (amount <= 0 || !payFile) return;
                  setSubmittingPay(true);
                  setError("");
                  setPaySuccess("");
                  try {
                    await api.parentPortal.submitReceipt(amount, payFile, payNote);
                    setPaySuccess(
                      "Чек отправлен. Репетитор проверит оплату и зачислит средства на баланс."
                    );
                    setPayFile(null);
                    setPayNote("");
                    await loadData();
                  } catch (e) {
                    setError(e instanceof ApiError ? e.message : "Ошибка отправки");
                  } finally {
                    setSubmittingPay(false);
                  }
                }}
                className="px-5 py-2.5 rounded-xl bg-brand-green text-white text-sm font-medium disabled:opacity-50"
              >
                {submittingPay ? "Отправка…" : "Отправить чек"}
              </button>
            </>
          ) : (
            <p className="text-sm text-amber-700">
              Репетитор ещё не указал реквизиты. Свяжитесь с ним напрямую.
            </p>
          )}

          {receipts.length > 0 && (
            <div className="pt-4 border-t space-y-2">
              <h3 className="text-sm font-medium text-slate-700">Ваши заявки на оплату</h3>
              <ul className="space-y-2 text-sm">
                {receipts.map((r) => (
                  <li key={r.id} className="flex justify-between gap-2 p-2 rounded-lg bg-slate-50">
                    <span>
                      {formatMoney(r.amount)} ·{" "}
                      {new Date(r.created_at).toLocaleDateString("ru-RU")}
                    </span>
                    <span
                      className={
                        r.status === "confirmed"
                          ? "text-emerald-700"
                          : r.status === "rejected"
                            ? "text-red-600"
                            : "text-amber-700"
                      }
                    >
                      {r.status === "confirmed"
                        ? "Зачислено"
                        : r.status === "rejected"
                          ? "Отклонено"
                          : "На проверке"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="bg-white rounded-2xl border p-6 shadow-sm">
          <div className="flex flex-wrap justify-between items-start gap-3">
            <div>
              <h2 className="font-semibold text-brand-blue">Итоги месяца</h2>
              <p className="text-sm text-slate-500 mt-1">Уроки, темы и оплаты</p>
            </div>
            <input
              type="month"
              value={reportMonth}
              onChange={(e) => setReportMonth(e.target.value)}
              className="px-3 py-2 rounded-xl border text-sm"
            />
          </div>
          {report ? (
            <div className="mt-4 space-y-2 text-sm">
              <p>
                Уроков проведено: <strong>{report.lessons_conducted}</strong> из {report.lessons_total}
              </p>
              <p>
                Оплаты за месяц: <strong>{formatMoney(report.payments_total)}</strong> · баланс{" "}
                {formatMoney(report.balance)}
              </p>
              {report.topics_covered.length > 0 && (
                <p className="text-slate-600">
                  Темы: {report.topics_covered.slice(0, 6).join(", ")}
                  {report.topics_covered.length > 6 ? "…" : ""}
                </p>
              )}
              <a
                href={api.parentPortal.reportPdfUrl(reportMonth)}
                className="inline-block mt-2 text-sm text-brand-blue hover:underline"
              >
                Скачать PDF
              </a>
            </div>
          ) : (
            <p className="text-sm text-slate-500 mt-3">Нет данных за выбранный месяц</p>
          )}
        </section>

        <section className="bg-white rounded-2xl border p-6 shadow-sm">
          <h2 className="font-semibold text-brand-blue">Домашние задания</h2>
          <p className="text-sm text-slate-500 mt-1">Статус сдачи (без содержания заданий)</p>
          {homeworkStatus.length === 0 ? (
            <p className="text-sm text-slate-500 mt-3">Пока нет заданий</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {homeworkStatus.map((h) => (
                <li
                  key={h.homework_id}
                  className="flex justify-between items-center text-sm border-b border-slate-100 pb-2"
                >
                  <span>{new Date(h.lesson_date).toLocaleDateString("ru-RU")}</span>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded-lg ${
                      h.status === "reviewed"
                        ? "bg-emerald-100 text-emerald-800"
                        : h.status === "needs_revision"
                          ? "bg-amber-100 text-amber-800"
                          : h.status === "submitted"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {h.status_label}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bg-white rounded-2xl border p-6 shadow-sm">
          <h2 className="font-semibold text-brand-blue">Расписание занятий</h2>
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
      </main>
    </div>
  );
}

export default function ParentPortalPage() {
  return (
    <Suspense fallback={<LoadingSpinner label="Загрузка..." />}>
      <ParentPortalContent />
    </Suspense>
  );
}
