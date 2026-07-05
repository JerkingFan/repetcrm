"use client";

import { useEffect, useState } from "react";
import { api, authFetch, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { toast } from "@/lib/toast";

function currentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function ParentPortalPanel({ studentId }: { studentId: number }) {
  const [portalUrl, setPortalUrl] = useState("");
  const [portalToken, setPortalToken] = useState("");
  const [calendarFeedUrl, setCalendarFeedUrl] = useState("");
  const [reportMonth, setReportMonth] = useState(currentMonth);
  const [report, setReport] = useState<Awaited<
    ReturnType<typeof api.students.getParentReport>
  > | null>(null);
  const [sending, setSending] = useState(false);

  const reload = () => {
    api.students.getParentPortalLink(studentId).then((r) => {
      setPortalUrl(r.parent_portal_url);
      setPortalToken(r.parent_portal_token);
      setCalendarFeedUrl(api.parentPortal.calendarFeedUrl(r.parent_portal_token));
    });
  };

  useEffect(() => {
    reload();
  }, [studentId]);

  useEffect(() => {
    api.students.getParentReport(studentId, reportMonth).then(setReport).catch(() => setReport(null));
  }, [studentId, reportMonth]);

  const copyLink = () => {
    if (!portalUrl) return;
    navigator.clipboard.writeText(portalUrl).then(
      () => toast("Ссылка для родителя скопирована", "success"),
      () => toast("Не удалось скопировать", "error")
    );
  };

  const copyCalendar = () => {
    if (!calendarFeedUrl) return;
    navigator.clipboard.writeText(calendarFeedUrl).then(
      () => toast("Ссылка на календарь скопирована", "success"),
      () => toast("Не удалось скопировать", "error")
    );
  };

  const downloadReport = async () => {
    const res = await authFetch(api.students.parentReportPdfUrl(studentId, reportMonth));
    if (!res.ok) {
      toast("Не удалось скачать отчёт", "error");
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `otchet-${reportMonth}.pdf`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const sendReport = async () => {
    setSending(true);
    try {
      await api.students.sendParentReport(studentId, reportMonth);
      toast("Отчёт отправлен родителю", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка отправки", "error");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mt-8 space-y-6">
      <div className="p-6 rounded-2xl bg-white border shadow-sm space-y-3">
        <h2 className="font-semibold text-brand-blue">Кабинет родителя</h2>
        <p className="text-sm text-slate-500">
          Расписание, баланс и оплата — для родителя (плательщика). Без домашних заданий.
        </p>
        <p className="text-xs text-slate-400">
          Email-напоминания (урок завтра, низкий баланс, оплата) уходят на адрес родителя из карточки
          ученика, если включено «уведомлять по email» и настроен SMTP в настройках сервера.
        </p>
        <input readOnly value={portalUrl} className="w-full px-3 py-2 rounded-xl border text-sm" />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={copyLink}
            className="px-4 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium"
          >
            Копировать ссылку
          </button>
          <button
            type="button"
            onClick={() =>
              api.students.regenerateParentPortalLink(studentId).then((r) => {
                setPortalUrl(r.parent_portal_url);
                setPortalToken(r.parent_portal_token);
                setCalendarFeedUrl(api.parentPortal.calendarFeedUrl(r.parent_portal_token));
                toast("Новая ссылка для родителя", "success");
              })
            }
            className="px-4 py-2 rounded-xl border text-sm"
          >
            Новая ссылка
          </button>
          <button type="button" onClick={copyCalendar} className="px-4 py-2 rounded-xl border text-sm">
            Подписка (.ics)
          </button>
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-white border shadow-sm space-y-4">
        <h2 className="font-semibold text-brand-blue">Отчёт для родителя</h2>
        <p className="text-sm text-slate-500">Итоги месяца: уроки, темы, ДЗ, оплаты</p>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="month"
            value={reportMonth}
            onChange={(e) => setReportMonth(e.target.value)}
            className="px-3 py-2 rounded-xl border text-sm"
          />
          <button type="button" onClick={downloadReport} className="px-4 py-2 rounded-xl border text-sm">
            Скачать PDF
          </button>
          <button
            type="button"
            onClick={sendReport}
            disabled={sending}
            className="px-4 py-2 rounded-xl bg-brand-green text-white text-sm font-medium disabled:opacity-50"
          >
            {sending ? "Отправка…" : "Отправить родителю"}
          </button>
        </div>
        {report && (
          <div className="text-sm text-slate-600 space-y-1 pt-2 border-t">
            <p>
              <strong>{report.month_label}</strong> · уроков {report.lessons_conducted}/
              {report.lessons_total}
            </p>
            <p>Оплаты за месяц: {formatMoney(report.payments_total)} · баланс {formatMoney(report.balance)}</p>
            {report.topics_covered.length > 0 && (
              <p className="text-xs text-slate-500 line-clamp-2">
                Темы: {report.topics_covered.slice(0, 5).join(", ")}
                {report.topics_covered.length > 5 ? "…" : ""}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
