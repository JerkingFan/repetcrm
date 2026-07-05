"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { HomeworkPrefs, defaultHomeworkPrefs } from "@/lib/homeworkPrefs";
import { toast } from "@/lib/toast";

type ChecklistRow = {
  topic: string;
  work_type: string;
  difficulty: string;
  understanding: number;
};

export default function HomeworkTemplatesPanel({
  lessonId,
  hasHomework,
  onApplied,
  onPrefsLoaded,
  onRowsLoaded,
}: {
  lessonId: number;
  hasHomework: boolean;
  onApplied: () => void;
  onPrefsLoaded: (prefs: HomeworkPrefs) => void;
  onRowsLoaded: (rows: ChecklistRow[]) => void;
}) {
  const [templates, setTemplates] = useState<Awaited<ReturnType<typeof api.homeworkTemplates.list>>>([]);
  const [selected, setSelected] = useState("");
  const [copyText, setCopyText] = useState(true);
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [showSave, setShowSave] = useState(false);

  const reload = () => {
    api.homeworkTemplates.list().then(setTemplates).catch(() => setTemplates([]));
  };

  useEffect(() => {
    reload();
  }, []);

  const applyTemplate = async () => {
    if (!selected) return;
    setApplying(true);
    try {
      const lesson = await api.homeworkTemplates.applyToLesson(Number(selected), lessonId, copyText);
      if (lesson.checklist_items?.length) {
        onRowsLoaded(
          lesson.checklist_items.map((i) => ({
            topic: i.topic,
            work_type: i.work_type,
            difficulty: i.difficulty,
            understanding: i.understanding,
          }))
        );
      }
      if (lesson.homework_prefs) {
        onPrefsLoaded({ ...defaultHomeworkPrefs(), ...(lesson.homework_prefs as HomeworkPrefs) });
      }
      onApplied();
      toast("Шаблон применён", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка", "error");
    } finally {
      setApplying(false);
    }
  };

  const saveTemplate = async () => {
    if (!templateName.trim()) return;
    setSaving(true);
    try {
      await api.homeworkTemplates.fromLesson(lessonId, templateName.trim(), true);
      setTemplateName("");
      setShowSave(false);
      reload();
      toast("Шаблон сохранён", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-6 pt-6 border-t space-y-3">
      <h3 className="font-medium text-slate-800">Шаблоны ДЗ</h3>
      <p className="text-sm text-slate-500">
        Сохраните удачную генерацию и примените к другому занятию
      </p>

      <div className="flex flex-col sm:flex-row gap-2">
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="flex-1 px-3 py-2 rounded-xl border text-sm"
        >
          <option value="">Выберите шаблон…</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
              {t.preview ? ` — ${t.preview.slice(0, 40)}` : ""}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={applyTemplate}
          disabled={!selected || applying}
          className="px-4 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium disabled:opacity-50"
        >
          {applying ? "…" : "Применить"}
        </button>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={copyText}
          onChange={(e) => setCopyText(e.target.checked)}
          className="rounded"
        />
        Скопировать текст ДЗ (без повторной генерации)
      </label>

      {hasHomework && (
        <div className="pt-2">
          {!showSave ? (
            <button
              type="button"
              onClick={() => setShowSave(true)}
              className="text-sm text-brand-blue hover:underline"
            >
              Сохранить текущее ДЗ как шаблон
            </button>
          ) : (
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="Название шаблона"
                className="flex-1 px-3 py-2 rounded-xl border text-sm"
              />
              <button
                type="button"
                onClick={saveTemplate}
                disabled={saving || !templateName.trim()}
                className="px-4 py-2 rounded-xl bg-brand-green text-white text-sm font-medium disabled:opacity-50"
              >
                {saving ? "…" : "Сохранить"}
              </button>
              <button
                type="button"
                onClick={() => setShowSave(false)}
                className="px-3 py-2 text-sm text-slate-500"
              >
                Отмена
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
