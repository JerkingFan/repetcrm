"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { SUBJECT_PRESETS, GRADE_PRESETS } from "@/lib/constants";
import { toast } from "@/lib/toast";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function PromptsMarketplacePage() {
  const [templates, setTemplates] = useState<Awaited<ReturnType<typeof api.promptTemplates.list>>>(
    []
  );
  const [subject, setSubject] = useState("");
  const [grade, setGrade] = useState("");
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    api.promptTemplates
      .list({ subject: subject || undefined, grade: grade || undefined })
      .then(setTemplates)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [subject, grade]);

  const install = async (id: number) => {
    setInstalling(id);
    try {
      const r = await api.promptTemplates.install(id);
      toast(r.message, "success");
      load();
    } catch {
      toast("Не удалось установить", "error");
    } finally {
      setInstalling(null);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-blue">Маркетплейс промптов ДЗ</h1>
      <p className="mt-1 text-slate-500">
        Готовые настройки генерации по предметам и классам — добавляются в «Мои шаблоны»
      </p>

      <div className="mt-6 flex flex-wrap gap-3">
        <select
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="px-3 py-2 rounded-xl border text-sm"
        >
          <option value="">Все предметы</option>
          {SUBJECT_PRESETS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={grade}
          onChange={(e) => setGrade(e.target.value)}
          className="px-3 py-2 rounded-xl border text-sm"
        >
          <option value="">Все классы</option>
          {GRADE_PRESETS.map((g) => (
            <option key={g} value={g}>
              {g} класс
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <LoadingSpinner label="Загрузка каталога..." />
      ) : templates.length === 0 ? (
        <p className="mt-8 text-slate-500">Нет промптов по выбранным фильтрам</p>
      ) : (
        <div className="mt-8 grid sm:grid-cols-2 gap-4">
          {templates.map((t) => (
            <article
              key={t.id}
              className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex flex-col"
            >
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="px-2 py-0.5 rounded-full bg-blue-50 text-brand-blue">
                  {t.subject}
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {t.grade} класс
                </span>
              </div>
              <h2 className="mt-3 font-semibold text-slate-800">{t.title}</h2>
              <p className="mt-2 text-sm text-slate-500 flex-1">{t.description}</p>
              <div className="mt-4 flex items-center justify-between gap-2">
                <span className="text-xs text-slate-400">{t.use_count} установок</span>
                {t.installed ? (
                  <span className="text-sm text-brand-green font-medium">Установлено ✓</span>
                ) : (
                  <button
                    type="button"
                    onClick={() => install(t.id)}
                    disabled={installing === t.id}
                    className="px-4 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium disabled:opacity-50"
                  >
                    {installing === t.id ? "…" : "Добавить"}
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
