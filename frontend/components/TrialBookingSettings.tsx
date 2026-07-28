"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

const DEFAULT_HOURS = [0, 1, 2, 3, 4].map((weekday) => ({
  weekday,
  from_time: "10:00",
  to_time: "18:00",
}));

type HoursSlot = { weekday: number; from_time: string; to_time: string };

function mergeHours(slots: HoursSlot[]): HoursSlot[] {
  const byDay = new Map(slots.map((s) => [s.weekday, s]));
  return WEEKDAYS.map((_, weekday) => byDay.get(weekday) || { weekday, from_time: "", to_time: "" });
}

export default function TrialBookingSettings() {
  const [slug, setSlug] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [hours, setHours] = useState<HoursSlot[]>(mergeHours(DEFAULT_HOURS));
  const [replyText, setReplyText] = useState("");
  const [bookingUrl, setBookingUrl] = useState("");
  const [leads, setLeads] = useState<Awaited<ReturnType<typeof api.booking.listLeads>>>([]);
  const [saving, setSaving] = useState(false);

  const reloadLeads = () => api.booking.listLeads().then(setLeads).catch(() => setLeads([]));

  useEffect(() => {
    api.booking.getSettings().then((s) => {
      setSlug(s.booking_slug);
      setEnabled(s.booking_enabled);
      setHours(mergeHours(s.booking_hours.length ? s.booking_hours : DEFAULT_HOURS));
      setReplyText(s.booking_reply_text);
      setBookingUrl(s.booking_url || (s.booking_slug ? api.booking.publicUrl(s.booking_slug) : ""));
    });
    reloadLeads();
  }, []);

  const toggleDay = (weekday: number, on: boolean) => {
    setHours((prev) => {
      const rest = prev.filter((h) => h.weekday !== weekday);
      if (!on) return mergeHours(rest);
      return mergeHours([
        ...rest,
        { weekday, from_time: "10:00", to_time: "18:00" },
      ]);
    });
  };

  const updateHour = (weekday: number, field: "from_time" | "to_time", value: string) => {
    setHours((prev) =>
      prev.map((h) => (h.weekday === weekday ? { ...h, [field]: value } : h))
    );
  };

  const activeHours = () =>
    hours.filter((h) => h.from_time && h.to_time && h.from_time < h.to_time);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.booking.updateSettings({
        booking_slug: slug,
        booking_enabled: enabled,
        booking_hours: activeHours(),
        booking_reply_text: replyText,
      });
      setSlug(updated.booking_slug);
      setEnabled(updated.booking_enabled);
      setBookingUrl(updated.booking_url || api.booking.publicUrl(updated.booking_slug));
      toast("Настройки записи сохранены", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка сохранения", "error");
    } finally {
      setSaving(false);
    }
  };

  const copyLink = () => {
    const url = bookingUrl || api.booking.publicUrl(slug);
    if (!url) return;
    navigator.clipboard.writeText(url).then(
      () => toast("Ссылка скопирована", "success"),
      () => toast("Не удалось скопировать", "error")
    );
  };

  const statusLabel: Record<string, string> = {
    new: "Новая",
    contacted: "Связались",
    scheduled: "Назначено",
    declined: "Отказ",
  };

  return (
    <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-5">
      <div>
        <h2 className="font-semibold text-brand-blue">Запись на пробный урок</h2>
        <p className="text-sm text-slate-500 mt-1">
          Публичная ссылка для Instagram, Telegram и сайта. Заявки попадают в CRM как лиды.
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="rounded"
        />
        Страница записи включена
      </label>

      <div>
        <label className="block text-sm font-medium mb-1">Адрес страницы</label>
        <div className="flex gap-2">
          <span className="px-3 py-2 rounded-xl border bg-slate-50 text-sm text-slate-500 shrink-0">
            /book/
          </span>
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
            className="flex-1 px-3 py-2 rounded-xl border text-sm"
            placeholder="ivan-math"
          />
        </div>
      </div>

      {(bookingUrl || slug) && (
        <div className="flex flex-wrap gap-2">
          <input
            readOnly
            value={bookingUrl || api.booking.publicUrl(slug)}
            className="flex-1 min-w-[200px] px-3 py-2 rounded-xl border text-sm"
          />
          <button type="button" onClick={copyLink} className="px-4 py-2 rounded-xl border text-sm">
            Копировать
          </button>
        </div>
      )}

      <div>
        <p className="text-sm font-medium mb-2">Рабочие часы (слоты по часу)</p>
        <div className="space-y-2">
          {WEEKDAYS.map((label, weekday) => {
            const slot = hours.find((h) => h.weekday === weekday);
            const on = Boolean(slot?.from_time && slot?.to_time);
            return (
              <div key={weekday} className="flex flex-wrap items-center gap-2 text-sm">
                <label className="w-8 flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={on}
                    onChange={(e) => toggleDay(weekday, e.target.checked)}
                  />
                  {label}
                </label>
                {on && slot && (
                  <>
                    <input
                      type="time"
                      value={slot.from_time}
                      onChange={(e) => updateHour(weekday, "from_time", e.target.value)}
                      className="px-2 py-1 rounded-lg border"
                    />
                    <span className="text-slate-400">—</span>
                    <input
                      type="time"
                      value={slot.to_time}
                      onChange={(e) => updateHour(weekday, "to_time", e.target.value)}
                      className="px-2 py-1 rounded-lg border"
                    />
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Автоответ родителю (email)</label>
        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          rows={4}
          className="w-full px-3 py-2 rounded-xl border text-sm"
          placeholder="Спасибо за заявку! Свяжусь с вами в течение дня…"
        />
        <p className="text-xs text-slate-400 mt-1">
          Можно использовать {"{tutor_name}"} — подставится ваше имя
        </p>
      </div>

      <button
        type="button"
        onClick={save}
        disabled={saving}
        className="px-5 py-2.5 rounded-xl bg-brand-blue text-white text-sm font-medium disabled:opacity-50"
      >
        {saving ? "Сохранение…" : "Сохранить"}
      </button>

      {leads.length > 0 && (
        <div className="pt-4 border-t space-y-3">
          <h3 className="font-medium text-sm">Заявки</h3>
          <ul className="space-y-2">
            {leads.map((lead) => (
              <li key={lead.id} className="text-sm border rounded-xl p-3 space-y-1">
                <div className="flex flex-wrap justify-between gap-2">
                  <span className="font-medium">
                    {lead.child_name} · {lead.subject} · {lead.grade} кл.
                  </span>
                  <select
                    value={lead.status}
                    onChange={async (e) => {
                      await api.booking.updateLeadStatus(lead.id, e.target.value);
                      reloadLeads();
                    }}
                    className="text-xs px-2 py-1 rounded-lg border"
                  >
                    {Object.entries(statusLabel).map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="text-slate-500">
                  {lead.parent_name} · {lead.parent_email}
                  {lead.parent_phone ? ` · ${lead.parent_phone}` : ""}
                </p>
                <p className="text-slate-500">
                  Слот: {lead.preferred_date} {lead.preferred_time}
                </p>
                <div className="flex flex-wrap gap-3 pt-1">
                  <Link
                    href={`/lessons/new?student_id=${lead.student_id}&date=${lead.preferred_date}&time=${encodeURIComponent(lead.preferred_time)}&is_trial=1`}
                    className="text-brand-blue hover:underline text-xs font-medium"
                  >
                    В расписание →
                  </Link>
                  <Link
                    href={`/students/${lead.student_id}`}
                    className="text-slate-500 hover:underline text-xs"
                  >
                    Карточка ученика →
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
