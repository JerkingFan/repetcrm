"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getToken } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import ChipSelect from "@/components/ChipSelect";
import { SUBJECT_PRESETS, GRADE_PRESETS, TEACHING_FORMATS } from "@/lib/constants";
import Alert from "@/components/Alert";

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

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.me(token).then((u) => {
      setUser(u);
      setSubjects(u.subjects || []);
      setGradeLevels(u.grade_levels || []);
      setTeachingFormat(u.teaching_format || "both");
    });
    api.ai.status(token).then(setAiStatus).catch(() => setAiStatus(null));
  }, []);

  const saveProfile = async () => {
    const token = getToken();
    if (!token) return;
    setError("");
    try {
      await api.updateProfile(token, {
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

  const formatLabel =
    TEACHING_FORMATS.find((f) => f.id === teachingFormat)?.label || teachingFormat;

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-brand-blue">Настройки</h1>
      <p className="text-slate-500 text-sm mt-1">Профиль репетитора и параметры AI</p>

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

      <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-4">
        <div>
          <p className="text-sm text-slate-500">Имя</p>
          <p className="font-medium">{user?.name || "—"}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Email</p>
          <p className="font-medium">{user?.email || "—"}</p>
        </div>
        <div>
          <p className="text-sm text-slate-500">Формат занятий</p>
          <p className="font-medium">{formatLabel}</p>
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
          <p className="text-sm text-slate-500 mt-2">Загрузка статуса…</p>
        )}
      </div>
    </div>
  );
}
