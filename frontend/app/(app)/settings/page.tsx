"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, authFetch, ApiError, NotificationSettings, ImportResult } from "@/lib/api";
import ChipSelect from "@/components/ChipSelect";
import { SUBJECT_PRESETS, GRADE_PRESETS, TEACHING_FORMATS } from "@/lib/constants";
import Alert from "@/components/Alert";
import TrialBookingSettings from "@/components/TrialBookingSettings";
import PaymentRequisitesSettings from "@/components/PaymentRequisitesSettings";
import Skeleton from "@/components/Skeleton";

function SettingsCardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-4">
      <Skeleton className="h-6 w-40" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-5 w-48" />
        </div>
      ))}
    </div>
  );
}

export default function SettingsPage() {
  const [user, setUser] = useState<{
    name: string;
    email: string;
    subjects: string[];
    grade_levels: string[];
    teaching_format: string;
  } | null>(null);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [gradeLevels, setGradeLevels] = useState<string[]>([]);
  const [teachingFormat, setTeachingFormat] = useState("both");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [aiStatus, setAiStatus] = useState<Awaited<ReturnType<typeof api.ai.status>> | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");

  const [notify, setNotify] = useState<NotificationSettings | null>(null);
  const [notifySaved, setNotifySaved] = useState(false);
  const [importMsg, setImportMsg] = useState("");

  const downloadExport = async (url: string, filename: string) => {
    const res = await authFetch(url);
    if (!res.ok) {
      setError("Ошибка экспорта");
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const handleImport = async (kind: "students" | "lessons", file: File) => {
    setError("");
    setImportMsg("");
    try {
      const result: ImportResult =
        kind === "students" ? await api.data.importStudents(file) : await api.data.importLessons(file);
      setImportMsg(
        `Импорт: создано ${result.created}, обновлено ${result.updated}, пропущено ${result.skipped}` +
          (result.errors.length ? `. Ошибки: ${result.errors.slice(0, 3).join("; ")}` : "")
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка импорта");
    }
  };

  useEffect(() => {
    api.me().then((u) => {
      setUser(u);
      setSubjects(u.subjects || []);
      setGradeLevels(u.grade_levels || []);
      setTeachingFormat(u.teaching_format || "both");
    });
    api.ai.status().then(setAiStatus).catch(() => setAiStatus(null));
    api.getNotificationSettings().then(setNotify).catch(() => setNotify(null));
  }, []);

  const saveProfile = async () => {
    setError("");
    try {
      await api.updateProfile({
        subjects,
        grade_levels: gradeLevels,
        teaching_format: teachingFormat,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка сохранения");
    }
  };

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg("");
    setError("");
    if (newPassword !== confirmPassword) {
      setError("Новые пароли не совпадают");
      return;
    }
    try {
      await api.changePassword(currentPassword, newPassword);
      setPasswordMsg("Пароль изменён");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка смены пароля");
    }
  };

  const saveNotifications = async () => {
    if (!notify) return;
    setError("");
    try {
      const updated = await api.updateNotificationSettings({
        notify_email: notify.notify_email,
        notify_telegram: notify.notify_telegram,
        notify_lesson_tomorrow: notify.notify_lesson_tomorrow,
        notify_unpaid: notify.notify_unpaid,
        notify_homework_ready: notify.notify_homework_ready,
        telegram_chat_id: notify.telegram_chat_id,
        contact_telegram: notify.contact_telegram || "",
        contact_url: notify.contact_url || "",
        hide_balance_in_portal: notify.hide_balance_in_portal !== false,
      });
      setNotify(updated);
      setNotifySaved(true);
      setTimeout(() => setNotifySaved(false), 3000);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка сохранения уведомлений");
    }
  };

  const formatLabel =
    TEACHING_FORMATS.find((f) => f.id === teachingFormat)?.label || teachingFormat;

  const toggleNotify = (key: keyof NotificationSettings, value: boolean) => {
    if (!notify) return;
    setNotify({ ...notify, [key]: value });
  };

  return (
    <div className="max-w-2xl">
      <h1 className="rc-page-title">Настройки</h1>
      <p className="text-slate-500 text-sm mt-1">Профиль, безопасность и уведомления</p>

      {error && (
        <div className="mt-4">
          <Alert message={error} onClose={() => setError("")} />
        </div>
      )}
      {saved && (
        <div className="mt-4">
          <Alert type="success" message="Профиль сохранён" />
        </div>
      )}
      {passwordMsg && (
        <div className="mt-4">
          <Alert type="success" message={passwordMsg} />
        </div>
      )}
      {notifySaved && (
        <div className="mt-4">
          <Alert type="success" message="Настройки уведомлений сохранены" />
        </div>
      )}
      {importMsg && (
        <div className="mt-4">
          <Alert type="success" message={importMsg} />
        </div>
      )}

      <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-4">
        <div>
          <p className="text-sm text-slate-500">Имя</p>
          <p className="font-medium">{user ? user.name : <Skeleton className="h-5 w-40" />}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Email</p>
          <p className="font-medium">{user ? user.email : <Skeleton className="h-5 w-56" />}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Формат занятий</p>
          <p className="font-medium">{user ? formatLabel : <Skeleton className="h-5 w-36" />}</p>
        </div>
        <Link
          href="/onboarding?retake=1"
          className="inline-block text-sm text-brand-blue hover:underline"
        >
          Пройти обзорный тур заново →
        </Link>
      </div>

      <form
        onSubmit={changePassword}
        className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-4"
      >
        <h2 className="font-semibold text-brand-blue">Смена пароля</h2>
        <div>
          <label className="block text-sm font-medium mb-1">Текущий пароль</label>
          <input
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Новый пароль</label>
          <input
            type="password"
            required
            minLength={10}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Повторите новый пароль</label>
          <input
            type="password"
            required
            minLength={10}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border"
          />
        </div>
        <button
          type="submit"
          className="w-full py-3 rounded-xl bg-brand-blue text-white font-semibold hover:bg-brand-ink"
        >
          Изменить пароль
        </button>
      </form>

      {notify ? (
        <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-4">
          <h2 className="font-semibold text-brand-blue">Напоминания</h2>
          <p className="text-sm text-slate-500">
            Email и Telegram. На сервере должны быть настроены SMTP и бот (
            {!notify.smtp_configured && <span className="text-amber-600">SMTP не настроен · </span>}
            {!notify.telegram_configured && <span className="text-amber-600">Telegram-бот не настроен</span>}
            {notify.smtp_configured && notify.telegram_configured && "всё настроено"}
            ).
          </p>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={notify.notify_email}
              onChange={(e) => toggleNotify("notify_email", e.target.checked)}
            />
            <span className="text-sm">Уведомления на email</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={notify.notify_telegram}
              onChange={(e) => toggleNotify("notify_telegram", e.target.checked)}
            />
            <span className="text-sm">Уведомления в Telegram</span>
          </label>
          {notify.notify_telegram && (
            <div>
              <label className="block text-sm font-medium mb-1">Telegram chat ID</label>
              <input
                type="text"
                value={notify.telegram_chat_id}
                onChange={(e) => setNotify({ ...notify, telegram_chat_id: e.target.value })}
                placeholder="Напишите боту /start и узнайте id у @userinfobot"
                className="w-full px-4 py-3 rounded-xl border"
              />
            </div>
          )}
          <div className="border-t pt-4 space-y-2">
            <p className="text-sm font-medium text-slate-700">О чём напоминать</p>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={notify.notify_lesson_tomorrow}
                onChange={(e) => toggleNotify("notify_lesson_tomorrow", e.target.checked)}
              />
              <span className="text-sm">Завтра урок</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={notify.notify_unpaid}
                onChange={(e) => toggleNotify("notify_unpaid", e.target.checked)}
              />
              <span className="text-sm">Неоплаченные занятия</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={notify.notify_homework_ready}
                onChange={(e) => toggleNotify("notify_homework_ready", e.target.checked)}
              />
              <span className="text-sm">ДЗ готово / дедлайн завтра</span>
            </label>
          </div>

          <div className="border-t pt-4 space-y-3">
            <p className="text-sm font-medium text-slate-700">Кабинет ученика</p>
            <div>
              <label className="block text-sm font-medium mb-1">Telegram для связи (@username)</label>
              <input
                type="text"
                value={notify.contact_telegram || ""}
                onChange={(e) => setNotify({ ...notify, contact_telegram: e.target.value })}
                placeholder="ivan_tutor"
                className="w-full px-4 py-3 rounded-xl border"
              />
              <p className="text-xs text-slate-400 mt-1">Кнопка «Написать репетитору» в кабинете</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Ссылка на урок по умолчанию</label>
              <input
                type="url"
                value={notify.contact_url || ""}
                onChange={(e) => setNotify({ ...notify, contact_url: e.target.value })}
                placeholder="https://meet.google.com/…"
                className="w-full px-4 py-3 rounded-xl border"
              />
              <p className="text-xs text-slate-400 mt-1">
                Если у занятия нет своей ссылки — подставится эта
              </p>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={notify.hide_balance_in_portal !== false}
                onChange={(e) =>
                  setNotify({ ...notify, hide_balance_in_portal: e.target.checked })
                }
              />
              <span className="text-sm">Скрыть баланс в кабинете ученика</span>
            </label>
          </div>
          <button
            type="button"
            onClick={saveNotifications}
            className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600"
          >
            Сохранить уведомления
          </button>
        </div>
      ) : (
        <SettingsCardSkeleton lines={5} />
      )}

      <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-8">
        <div>
          <p className="text-sm text-slate-500">Имя</p>
          <p className="font-medium">{user ? user.name : <Skeleton className="h-5 w-40" />}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Email</p>
          <p className="font-medium">{user ? user.email : <Skeleton className="h-5 w-56" />}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Формат занятий</p>
          <p className="font-medium">{user ? formatLabel : <Skeleton className="h-5 w-36" />}</p>
        </div>
        <Link
          href="/onboarding?retake=1"
          className="inline-block text-sm text-brand-blue hover:underline"
        >
          Пройти обзорный тур заново →
        </Link>
      </div>

      <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-8">
        <h2 className="font-semibold text-brand-blue">Предметы и классы</h2>
        <ChipSelect
          label="Предметы"
          hint="Используются при добавлении учеников"
          presets={SUBJECT_PRESETS}
          selected={subjects}
          onChange={setSubjects}
        />
        <ChipSelect
          label="Классы / уровни"
          presets={GRADE_PRESETS}
          selected={gradeLevels}
          onChange={setGradeLevels}
        />
        <div>
          <p className="text-sm font-medium text-slate-700 mb-3">Формат занятий</p>
          <div className="grid gap-2">
            {TEACHING_FORMATS.map((f) => (
              <label
                key={f.id}
                className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer ${
                  teachingFormat === f.id ? "border-brand-green bg-emerald-50" : "border-slate-200"
                }`}
              >
                <input
                  type="radio"
                  checked={teachingFormat === f.id}
                  onChange={() => setTeachingFormat(f.id)}
                />
                <span className="text-sm">{f.label}</span>
              </label>
            ))}
          </div>
        </div>
        <button
          onClick={saveProfile}
          className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600"
        >
          Сохранить профиль
        </button>
      </div>

      <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-4">
        <h2 className="font-semibold text-brand-blue">Экспорт и импорт</h2>
        <p className="text-sm text-slate-500">
          CSV с BOM — открывается в Excel. Ученики и занятия с оплатами для отчётов и переноса на сайт.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => downloadExport(api.data.exportStudentsUrl(), "students.csv")}
            className="px-4 py-2 rounded-xl border text-sm font-medium hover:bg-slate-50"
          >
            Экспорт учеников
          </button>
          <button
            type="button"
            onClick={() => downloadExport(api.data.exportLessonsUrl(), "lessons.csv")}
            className="px-4 py-2 rounded-xl border text-sm font-medium hover:bg-slate-50"
          >
            Экспорт занятий
          </button>
          <button
            type="button"
            onClick={() => downloadExport(api.calendar.tutorIcsUrl(), "tutor-schedule.ics")}
            className="px-4 py-2 rounded-xl border text-sm font-medium hover:bg-slate-50"
          >
            Календарь репетитора (.ics)
          </button>
        </div>
        <div className="grid sm:grid-cols-2 gap-4 pt-2">
          <label className="block">
            <span className="text-sm font-medium">Импорт учеников (CSV)</span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="mt-2 block w-full text-sm"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleImport("students", f);
                e.target.value = "";
              }}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Импорт занятий (CSV)</span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="mt-2 block w-full text-sm"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleImport("lessons", f);
                e.target.value = "";
              }}
            />
          </label>
        </div>
      </div>

      <TrialBookingSettings />

      <PaymentRequisitesSettings />

      <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm">
        <p className="text-sm font-medium text-brand-blue">AI-статус</p>
        {aiStatus ? (
          <div className="mt-3 space-y-2 text-sm">
            <p className="flex items-center gap-2">
              <span
                className={`inline-block w-2.5 h-2.5 rounded-full ${
                  aiStatus.local_llm.available ? "bg-emerald-500" : "bg-red-500"
                }`}
              />
              {aiStatus.local_llm.available
                ? [aiStatus.local_llm.model_file, aiStatus.local_llm.eta_hint].filter(Boolean).join(" · ") || "Модель доступна"
                : "Нейросеть недоступна"}
            </p>
            {!aiStatus.local_llm.available && (
              <p className="text-slate-500">
                Проверьте настройки AI и подключение к интернету.
              </p>
            )}
          </div>
        ) : (
          <div className="mt-3 space-y-2">
            <Skeleton className="h-4 w-52" />
            <Skeleton className="h-4 w-44" />
          </div>
        )}
      </div>
    </div>
  );
}
