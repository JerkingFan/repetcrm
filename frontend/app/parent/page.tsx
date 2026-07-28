"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { formatLessonTime } from "@/lib/calendar";
import { formatMoney } from "@/lib/currency";
import {
  formatRuDate,
  formatRuWeekday,
  isToday,
  submissionChipClass,
} from "@/lib/portalUi";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";
import PortalShell, { PortalCard, PortalEmpty } from "@/components/portal/PortalShell";

type ParentTab = "home" | "pay" | "homework" | "schedule" | "report";

const TABS: { id: ParentTab; label: string }[] = [
  { id: "home", label: "Главная" },
  { id: "pay", label: "Оплата" },
  { id: "homework", label: "ДЗ" },
  { id: "schedule", label: "Уроки" },
  { id: "report", label: "Отчёт" },
];

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
  const [tab, setTab] = useState<ParentTab>("home");
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

  const activePackage = useMemo(
    () => packages.find((p) => p.is_active && p.lessons_remaining > 0),
    [packages]
  );
  const nextLesson = lessons.find((l) => !l.is_conducted) || lessons[0] || null;
  const hwPending = homeworkStatus.filter(
    (h) => h.status === "not_submitted" || h.status === "needs_revision"
  ).length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner label="Вход в кабинет родителя…" />
      </div>
    );
  }

  if (!info) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-[radial-gradient(ellipse_at_top,_#e8eefc_0%,_#f8fafc_50%)]">
        <div className="max-w-sm w-full text-center space-y-4 rounded-2xl border bg-white p-8 shadow-sm">
          <p className="text-[11px] font-semibold tracking-wide uppercase text-brand-blue/70">
            RepetCRM
          </p>
          <h1 className="text-2xl font-bold text-brand-blue">Кабинет родителя</h1>
          {error ? (
            <Alert message={error} />
          ) : (
            <p className="text-slate-500 text-sm">Нужна персональная ссылка от репетитора.</p>
          )}
        </div>
      </div>
    );
  }

  const titles: Record<ParentTab, string> = {
    home: info.parent_name ? `Здравствуйте, ${info.parent_name}` : "Кабинет родителя",
    pay: "Оплата",
    homework: "Домашние задания",
    schedule: "Расписание",
    report: "Итоги месяца",
  };

  return (
    <PortalShell
      title={titles[tab]}
      subtitle={`${info.student_name}${info.tutor_name ? ` · ${info.tutor_name}` : ""}`}
    >
      {error && <Alert message={error} onClose={() => setError("")} />}

      {tab === "home" && (
        <>
          <PortalCard className="overflow-hidden">
            <div className="bg-gradient-to-br from-brand-blue to-[#2a4db0] px-5 py-5 text-white">
              <p className="text-sm text-white/75">Ученик</p>
              <h2 className="text-2xl font-bold">{info.student_name}</h2>
              <p className="text-sm text-white/80 mt-1">
                {[info.subject, info.grade].filter(Boolean).join(" · ")}
              </p>
              <div className="mt-4 flex justify-between items-end gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-white/60">Баланс</p>
                  <p className="text-lg font-semibold">{formatMoney(info.balance)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setTab("pay")}
                  className="px-3.5 py-2 rounded-xl bg-white/15 text-sm font-medium"
                >
                  Оплатить
                </button>
              </div>
              {activePackage && (
                <p className="text-xs text-white/70 mt-3">
                  Абонемент «{activePackage.name}»: {activePackage.lessons_remaining} из{" "}
                  {activePackage.lessons_total} занятий
                </p>
              )}
            </div>
          </PortalCard>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTab("homework")}
              className="rounded-2xl border bg-white p-4 text-left shadow-sm"
            >
              <p className="text-2xl font-bold text-brand-blue">{hwPending}</p>
              <p className="text-sm text-slate-600">ДЗ без сдачи</p>
            </button>
            <button
              type="button"
              onClick={() => setTab("report")}
              className="rounded-2xl border bg-white p-4 text-left shadow-sm"
            >
              <p className="text-sm font-semibold text-brand-blue">Отчёт</p>
              <p className="text-sm text-slate-500 mt-1">Итоги месяца</p>
            </button>
          </div>

          <PortalCard className="p-5">
            <h3 className="font-semibold text-slate-800 mb-3">Ближайший урок</h3>
            {nextLesson ? (
              <div className="flex gap-3 items-center">
                <div
                  className={`w-14 rounded-xl text-center py-2 ${
                    isToday(nextLesson.lesson_date)
                      ? "bg-emerald-50 text-emerald-800"
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
                <div>
                  <p className="font-medium">{formatRuDate(nextLesson.lesson_date)}</p>
                  <p className="text-sm text-slate-500">
                    {formatLessonTime(nextLesson.lesson_time)} · {nextLesson.duration_minutes} мин
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Ближайших занятий нет</p>
            )}
          </PortalCard>
        </>
      )}

      {tab === "pay" && (
        <PortalCard className="p-5 space-y-4">
          <p className="text-sm text-slate-500">
            Переведите сумму по реквизитам и прикрепите чек. После проверки средства зачислятся на
            баланс {info.student_name}.
          </p>
          {paymentDetails?.has_requisites ? (
            <>
              <pre className="text-sm bg-slate-50 border rounded-xl p-4 whitespace-pre-wrap font-sans">
                {paymentDetails.payment_details}
              </pre>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="text-xs text-slate-500">Сумма (Br)</span>
                  <input
                    type="number"
                    min={1}
                    value={payAmount}
                    onChange={(e) => setPayAmount(e.target.value)}
                    className="mt-1 w-full px-3 py-2.5 rounded-xl border text-sm"
                  />
                </label>
                <label className="block col-span-2">
                  <span className="text-xs text-slate-500">Чек (PDF, JPG, PNG)</span>
                  <input
                    type="file"
                    accept=".pdf,image/jpeg,image/png,image/webp"
                    onChange={(e) => setPayFile(e.target.files?.[0] || null)}
                    className="mt-1 block w-full text-sm"
                  />
                </label>
              </div>
              <input
                type="text"
                value={payNote}
                onChange={(e) => setPayNote(e.target.value)}
                placeholder="Комментарий (необязательно)"
                className="w-full px-3 py-2.5 rounded-xl border text-sm"
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
                    setPaySuccess("Чек отправлен. Репетитор проверит оплату.");
                    setPayFile(null);
                    setPayNote("");
                    await loadData();
                  } catch (e) {
                    setError(e instanceof ApiError ? e.message : "Ошибка отправки");
                  } finally {
                    setSubmittingPay(false);
                  }
                }}
                className="w-full px-5 py-3 rounded-xl bg-brand-green text-white text-sm font-semibold disabled:opacity-50"
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
              <h3 className="text-sm font-medium text-slate-700">Заявки на оплату</h3>
              {receipts.map((r) => (
                <div
                  key={r.id}
                  className="flex justify-between gap-2 p-3 rounded-xl bg-slate-50 text-sm"
                >
                  <span>
                    {formatMoney(r.amount)} · {new Date(r.created_at).toLocaleDateString("ru-RU")}
                  </span>
                  <span
                    className={
                      r.status === "confirmed"
                        ? "text-emerald-700 font-medium"
                        : r.status === "rejected"
                          ? "text-red-600 font-medium"
                          : "text-amber-700 font-medium"
                    }
                  >
                    {r.status === "confirmed"
                      ? "Зачислено"
                      : r.status === "rejected"
                        ? "Отклонено"
                        : "На проверке"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </PortalCard>
      )}

      {tab === "homework" && (
        <PortalCard>
          <div className="px-5 pt-4 pb-2">
            <p className="text-sm text-slate-500">Статус сдачи (без содержания заданий)</p>
          </div>
          {homeworkStatus.length === 0 ? (
            <PortalEmpty title="Пока нет заданий" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {homeworkStatus.map((h) => (
                <li
                  key={h.homework_id}
                  className="px-5 py-3.5 flex justify-between items-center gap-2 text-sm"
                >
                  <span className="font-medium text-slate-800">{formatRuDate(h.lesson_date)}</span>
                  <span
                    className={`text-[11px] font-medium px-2 py-0.5 rounded-lg ${submissionChipClass(
                      h.status
                    )}`}
                  >
                    {h.status_label}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </PortalCard>
      )}

      {tab === "schedule" && (
        <>
          <PortalCard className="p-4 flex items-center justify-between">
            <div>
              <p className="font-medium">Календарь</p>
              <p className="text-xs text-slate-500">Добавить в телефон</p>
            </div>
            <a
              href={api.parentPortal.calendarIcsUrl()}
              className="px-3 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium"
            >
              .ics
            </a>
          </PortalCard>
          <PortalCard>
            {lessons.length === 0 ? (
              <PortalEmpty title="Ближайших занятий нет" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {lessons.map((l) => (
                  <li key={l.id} className="px-5 py-3.5 flex justify-between text-sm">
                    <span className="font-medium">
                      {formatRuDate(l.lesson_date)} · {formatLessonTime(l.lesson_time)}
                    </span>
                    <span className="text-slate-500">{l.duration_minutes} мин</span>
                  </li>
                ))}
              </ul>
            )}
          </PortalCard>
        </>
      )}

      {tab === "report" && (
        <PortalCard className="p-5 space-y-4">
          <div className="flex flex-wrap justify-between items-center gap-3">
            <p className="text-sm text-slate-500">Уроки, темы и оплаты</p>
            <input
              type="month"
              value={reportMonth}
              onChange={(e) => setReportMonth(e.target.value)}
              className="px-3 py-2 rounded-xl border text-sm"
            />
          </div>
          {report ? (
            <div className="space-y-2 text-sm">
              <p>
                Уроков проведено: <strong>{report.lessons_conducted}</strong> из{" "}
                {report.lessons_total}
              </p>
              <p>
                Оплаты за месяц: <strong>{formatMoney(report.payments_total)}</strong> · баланс{" "}
                {formatMoney(report.balance)}
              </p>
              {report.topics_covered.length > 0 && (
                <p className="text-slate-600">
                  Темы: {report.topics_covered.slice(0, 8).join(", ")}
                  {report.topics_covered.length > 8 ? "…" : ""}
                </p>
              )}
              <a
                href={api.parentPortal.reportPdfUrl(reportMonth)}
                className="inline-flex mt-2 px-4 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium"
              >
                Скачать PDF
              </a>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Нет данных за выбранный месяц</p>
          )}
        </PortalCard>
      )}

      <nav className="fixed bottom-0 inset-x-0 z-40 border-t border-slate-200/80 bg-white/95 backdrop-blur-md safe-area-pb">
        <div className="max-w-lg mx-auto grid grid-cols-5">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`py-3 text-[11px] font-medium ${
                tab === t.id ? "text-brand-blue" : "text-slate-400"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>
    </PortalShell>
  );
}

export default function ParentPortalPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <LoadingSpinner label="Загрузка…" />
        </div>
      }
    >
      <ParentPortalContent />
    </Suspense>
  );
}
