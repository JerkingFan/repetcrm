"use client";

import { HomeworkPrefs } from "@/lib/homeworkPrefs";

type Props = {
  prefs: HomeworkPrefs;
  onChange: (prefs: HomeworkPrefs) => void;
  showOptional?: boolean;
};

function toggleInList(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((x) => x !== value) : [...list, value];
}

export default function LessonHomeworkForm({
  prefs,
  onChange,
  showOptional = true,
}: Props) {
  const set = <K extends keyof HomeworkPrefs>(key: K, value: HomeworkPrefs[K]) => {
    onChange({ ...prefs, [key]: value });
  };

  return (
    <div className="space-y-8">
      <div>
        <h3 className="font-medium text-brand-blue">Блок 2. Уровень ученика</h3>
        <p className="text-sm text-slate-500 mt-1">
          Обязательно: понимание материала и уровень по предмету
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Насколько ученик понял материал? (1–5) *
            </span>
            <select
              value={prefs.understanding_global}
              onChange={(e) => set("understanding_global", Number(e.target.value))}
              className="mt-1 w-full px-3 py-2 rounded-lg border text-sm"
            >
              <option value={5}>5 — всё отлично, может объяснить другому</option>
              <option value={4}>4 — хорошо, есть мелкие вопросы</option>
              <option value={3}>3 — средне, нужно закрепить</option>
              <option value={2}>2 — с трудом, много пробелов</option>
              <option value={1}>1 — почти не понял</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">
              Уровень ученика по предмету *
            </span>
            <select
              value={prefs.student_level}
              onChange={(e) => set("student_level", e.target.value)}
              className="mt-1 w-full px-3 py-2 rounded-lg border text-sm"
            >
              <option value="beginner">Начинающий</option>
              <option value="medium">Средний</option>
              <option value="advanced">Продвинутый</option>
              <option value="exam">Подготовка к экзамену</option>
            </select>
          </label>
        </div>
      </div>

      {showOptional && (
        <>
          <div>
            <h3 className="font-medium text-slate-800">Блок 1. Аспект занятия</h3>
            <p className="text-sm text-slate-500 mt-1">Для каждой темы ниже можно уточнить отдельно</p>
            <select
              value={prefs.focus_aspect}
              onChange={(e) => set("focus_aspect", e.target.value)}
              className="mt-2 w-full max-w-md px-3 py-2 rounded-lg border text-sm"
            >
              <option value="theory">Теория</option>
              <option value="practice">Практика</option>
              <option value="mixed">Смешанный формат</option>
              <option value="errors_review">Разбор ошибок / пробелы</option>
            </select>
          </div>

          <div>
            <h3 className="font-medium text-slate-800">Блок 3. Типы заданий</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {[
                ["practice_rules", "Формулы/правила"],
                ["text_problems", "Текстовые задачи"],
                ["tests", "Тесты"],
                ["creative", "Творческие"],
                ["multiple_choice", "С выбором ответа"],
                ["open_answer", "Открытый ответ"],
                ["translation", "Перевод"],
              ].map(([id, label]) => (
                <label
                  key={id}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm cursor-pointer ${
                    prefs.task_types.includes(id) ? "bg-blue-50 border-brand-blue" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={prefs.task_types.includes(id)}
                    onChange={() => set("task_types", toggleInList(prefs.task_types, id))}
                    className="rounded"
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Объём ДЗ</span>
              <select
                value={prefs.volume}
                onChange={(e) => set("volume", e.target.value)}
                className="mt-1 w-full px-3 py-2 rounded-lg border text-sm"
              >
                <option value="minimal">Минимальный (~15–20 мин)</option>
                <option value="standard">Стандартный (~30–40 мин)</option>
                <option value="extended">Расширенный (~60+ мин)</option>
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Сложность</span>
              <select
                value={prefs.difficulty_level}
                onChange={(e) => set("difficulty_level", e.target.value)}
                className="mt-1 w-full px-3 py-2 rounded-lg border text-sm"
              >
                <option value="basic">Базовый</option>
                <option value="medium">Средний</option>
                <option value="high">Высокий</option>
              </select>
            </label>
          </div>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Особые пожелания</span>
            <textarea
              value={prefs.special_notes}
              onChange={(e) => set("special_notes", e.target.value)}
              placeholder="Например: связать с футболом, избегать задач на движение…"
              className="mt-1 w-full px-3 py-2 rounded-lg border text-sm h-20"
            />
          </label>

          <div>
            <h3 className="font-medium text-slate-800">Блок 5. Формат и дополнения</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {[
                ["latex", "LaTeX"],
                ["pdf", "PDF"],
                ["chat_text", "Текст в чат"],
                ["html", "HTML"],
              ].map(([id, label]) => (
                <label
                  key={id}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm cursor-pointer ${
                    prefs.output_formats.includes(id) ? "bg-blue-50 border-brand-blue" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={prefs.output_formats.includes(id)}
                    onChange={() =>
                      set("output_formats", toggleInList(prefs.output_formats, id))
                    }
                    className="rounded"
                  />
                  {label}
                </label>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-4 text-sm">
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={prefs.include_cheatsheet}
                  onChange={(e) => set("include_cheatsheet", e.target.checked)}
                />
                Памятка по теме
              </label>
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={prefs.include_hints}
                  onChange={(e) => set("include_hints", e.target.checked)}
                />
                Подсказки
              </label>
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={prefs.include_examples}
                  onChange={(e) => set("include_examples", e.target.checked)}
                />
                Примеры решений
              </label>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
