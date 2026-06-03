"use client";

import { useEffect, useState } from "react";

const WHATS_NEW_VERSION = "2026-05-28-whiteboard-v1";
const STORAGE_KEY = "repetcrm_whats_new_seen";

export default function WhatsNewModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      const seen = localStorage.getItem(STORAGE_KEY);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (seen !== WHATS_NEW_VERSION) setOpen(true);
    } catch {
      // ignore
    }
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100]">
      <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-slate-100 overflow-hidden">
          <div className="p-6 lg:p-7">
            <p className="text-xs font-semibold text-brand-green uppercase tracking-wide">Обновление</p>
            <h2 className="mt-2 text-xl font-bold text-brand-blue">Что нового в RepetCRM</h2>

            <div className="mt-5 space-y-3 text-sm text-slate-700">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                <p className="font-semibold text-slate-900">Виртуальная доска</p>
                <p className="mt-1 text-slate-600">
                  Теперь у занятий есть доска: можно рисовать, писать текст и вставлять картинки по ссылке — даже без авторизации.
                </p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                <p className="font-semibold text-slate-900">Доска стала удобнее</p>
                <p className="mt-1 text-slate-600">
                  Сетка, плавные линии, зум колесом, вставка картинок через Ctrl+V и курсоры участников.
                </p>
              </div>
            </div>

            <div className="mt-6 flex flex-col sm:flex-row gap-3">
              <button
                className="flex-1 py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600"
                onClick={() => {
                  try {
                    localStorage.setItem(STORAGE_KEY, WHATS_NEW_VERSION);
                  } catch {
                    // ignore
                  }
                  setOpen(false);
                }}
              >
                Понял, спасибо
              </button>
              <button
                className="flex-1 py-3 rounded-xl border border-slate-200 font-semibold hover:bg-slate-50"
                onClick={() => setOpen(false)}
              >
                Закрыть
              </button>
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Покажем это окно один раз.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

