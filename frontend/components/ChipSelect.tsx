"use client";

import { useState } from "react";
import { XMarkIcon, PlusIcon } from "@heroicons/react/24/outline";

export default function ChipSelect({
  label,
  hint,
  presets,
  selected,
  onChange,
  allowCustom = true,
  customPlaceholder = "Добавить свой вариант...",
}: {
  label: string;
  hint?: string;
  presets: string[];
  selected: string[];
  onChange: (items: string[]) => void;
  allowCustom?: boolean;
  customPlaceholder?: string;
}) {
  const [custom, setCustom] = useState("");

  const toggle = (item: string) => {
    if (selected.includes(item)) {
      onChange(selected.filter((s) => s !== item));
    } else {
      onChange([...selected, item]);
    }
  };

  const addCustom = () => {
    const v = custom.trim();
    if (!v || selected.includes(v)) return;
    onChange([...selected, v]);
    setCustom("");
  };

  return (
    <div>
      <label className="block text-sm font-medium text-slate-700">{label}</label>
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {presets.map((item) => {
          const active = selected.includes(item);
          return (
            <button
              key={item}
              type="button"
              onClick={() => toggle(item)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition border ${
                active
                  ? "bg-brand-blue text-white border-brand-blue"
                  : "bg-white text-slate-600 border-slate-200 hover:border-brand-blue"
              }`}
            >
              {item}
            </button>
          );
        })}
      </div>
      {selected.filter((s) => !presets.includes(s)).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {selected
            .filter((s) => !presets.includes(s))
            .map((item) => (
              <span
                key={item}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-brand-green/10 text-brand-green text-sm border border-brand-green/30"
              >
                {item}
                <button type="button" onClick={() => toggle(item)} aria-label="Удалить">
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </span>
            ))}
        </div>
      )}
      {allowCustom && (
        <div className="mt-4 flex gap-2">
          <input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addCustom())}
            placeholder={customPlaceholder}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm outline-none focus:border-brand-green focus:ring-2 focus:ring-brand-green/20"
          />
          <button
            type="button"
            onClick={addCustom}
            className="px-4 py-2.5 rounded-xl border border-slate-200 hover:bg-slate-50"
          >
            <PlusIcon className="w-5 h-5 text-slate-600" />
          </button>
        </div>
      )}
      {selected.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">Выбрано: {selected.length}</p>
      )}
    </div>
  );
}
