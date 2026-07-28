"use client";

import { useEffect, useState } from "react";
import { api, authFetch } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { toast } from "@/lib/toast";

export default function StudentPortalPanel({ studentId }: { studentId: number }) {
  const [portalUrl, setPortalUrl] = useState("");
  const [portalToken, setPortalToken] = useState("");
  const [calendarFeedUrl, setCalendarFeedUrl] = useState("");
  const [packages, setPackages] = useState<
    Awaited<ReturnType<typeof api.students.listPackages>>
  >([]);
  const [balance, setBalance] = useState(0);
  const [pkgForm, setPkgForm] = useState({ name: "8 занятий", lessons_total: 8, price_per_lesson: 40 });
  const [topUp, setTopUp] = useState("");

  const reload = () => {
    api.students.getPortalLink(studentId).then((r) => {
      setPortalUrl(r.portal_url);
      setPortalToken(r.portal_token);
      setCalendarFeedUrl(api.calendar.feedIcsUrl(r.portal_token));
    });
    api.students.listPackages(studentId).then(setPackages);
    api.students.get<{ balance?: number }>(studentId).then((s) => setBalance(s.balance || 0));
  };

  useEffect(() => {
    reload();
  }, [studentId]);

  const copyLink = () => {
    if (!portalUrl) return;
    navigator.clipboard.writeText(portalUrl).then(
      () => toast("Ссылка скопирована", "success"),
      () => toast("Не удалось скопировать", "error")
    );
  };

  const downloadIcs = async () => {
    const res = await authFetch(api.calendar.studentIcsUrl(studentId));
    if (!res.ok) return;
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `student-${studentId}.ics`;
    a.click();
  };

  return (
    <div className="mt-8 space-y-6">
      <div className="p-6 rounded-2xl bg-white border shadow-sm space-y-3">
        <h2 className="font-semibold text-brand-blue">Кабинет ученика</h2>
        <p className="text-sm text-slate-500">
          Персональная ссылка: расписание, ДЗ, фото решений с AI-проверкой, баланс
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
              api.students.regeneratePortalLink(studentId).then((r) => {
                setPortalUrl(r.portal_url);
                toast("Новая ссылка создана", "success");
              })
            }
            className="px-4 py-2 rounded-xl border text-sm"
          >
            Новая ссылка
          </button>
          <button type="button" onClick={downloadIcs} className="px-4 py-2 rounded-xl border text-sm">
            Календарь (.ics)
          </button>
          <button
            type="button"
            onClick={() => {
              if (!calendarFeedUrl) return;
              navigator.clipboard.writeText(calendarFeedUrl).then(
                () => toast("Ссылка подписки для Google/Apple скопирована", "success"),
                () => toast("Не удалось скопировать", "error")
              );
            }}
            className="px-4 py-2 rounded-xl border text-sm"
          >
            Подписка (.ics)
          </button>
        </div>
        {calendarFeedUrl && (
          <input
            readOnly
            value={calendarFeedUrl}
            className="w-full px-3 py-2 rounded-xl border text-xs text-slate-500"
            title="URL для Google Calendar / Apple — добавить по URL"
          />
        )}
      </div>

      <div className="p-6 rounded-2xl bg-white border shadow-sm space-y-4">
        <h2 className="font-semibold text-brand-blue">Баланс и абонементы</h2>
        <p className="text-sm">
          Баланс: <strong>{formatMoney(balance)}</strong>
        </p>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="text-xs text-slate-500">Пополнить баланс (Br)</label>
            <input
              type="number"
              min={1}
              value={topUp}
              onChange={(e) => setTopUp(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border text-sm mt-1"
            />
          </div>
          <button
            type="button"
            onClick={() => {
              const amount = Number(topUp);
              if (amount > 0) {
                api.students.topUpBalance(studentId, amount).then((s) => {
                  setBalance(s.balance || 0);
                  setTopUp("");
                  toast("Баланс пополнен", "success");
                });
              }
            }}
            className="px-4 py-2 rounded-xl bg-brand-green text-white text-sm"
          >
            Пополнить
          </button>
        </div>

        {packages.length > 0 && (
          <ul className="space-y-2 text-sm">
            {packages.map((p) => (
              <li key={p.id} className="flex justify-between p-3 rounded-xl bg-slate-50">
                <span>{p.name}</span>
                <span>
                  {p.lessons_remaining}/{p.lessons_total} · {formatMoney(p.price_per_lesson)}/урок
                </span>
              </li>
            ))}
          </ul>
        )}

        <div className="grid sm:grid-cols-3 gap-2 pt-2">
          <input
            value={pkgForm.name}
            onChange={(e) => setPkgForm({ ...pkgForm, name: e.target.value })}
            className="px-3 py-2 rounded-xl border text-sm"
            placeholder="Название"
          />
          <input
            type="number"
            min={1}
            value={pkgForm.lessons_total}
            onChange={(e) => setPkgForm({ ...pkgForm, lessons_total: Number(e.target.value) })}
            className="px-3 py-2 rounded-xl border text-sm"
            placeholder="Занятий"
          />
          <input
            type="number"
            min={0}
            value={pkgForm.price_per_lesson}
            onChange={(e) => setPkgForm({ ...pkgForm, price_per_lesson: Number(e.target.value) })}
            className="px-3 py-2 rounded-xl border text-sm"
            placeholder="Br/урок"
          />
        </div>
        <button
          type="button"
          onClick={() =>
            api.students.createPackage(studentId, pkgForm).then(() => {
              reload();
              toast("Абонемент создан", "success");
            })
          }
          className="w-full py-2 rounded-xl border border-brand-green text-brand-green text-sm font-medium"
        >
          + Создать абонемент
        </button>
        <p className="text-xs text-slate-400">
          При проведении урока списание: сначала абонемент, затем баланс
        </p>

        <div className="pt-4 border-t space-y-2">
          <h3 className="text-sm font-medium text-slate-700">Оплата для родителя</h3>
          <p className="text-xs text-slate-500">
            Укажите реквизиты в настройках. Родитель переводит деньги и прикрепляет чек в кабинете
            /parent — вы подтверждаете на дашборде.
          </p>
        </div>
      </div>
    </div>
  );
}
