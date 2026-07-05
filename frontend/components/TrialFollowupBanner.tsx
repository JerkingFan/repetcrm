"use client";

import { toast } from "@/lib/toast";

export default function TrialFollowupBanner({
  message,
  title = "После пробного — отправьте родителю",
}: {
  message: string;
  title?: string;
}) {
  if (!message.trim()) return null;

  const copy = () => {
    navigator.clipboard.writeText(message).then(
      () => toast("Сообщение скопировано", "success"),
      () => toast("Не удалось скопировать", "error")
    );
  };

  return (
    <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 space-y-3">
      <div className="flex flex-wrap justify-between gap-2 items-start">
        <div>
          <p className="font-semibold text-emerald-900">{title}</p>
          <p className="text-sm text-emerald-800 mt-1">
            Ссылка на кабинет родителя, абонемент и оплата — готовый текст для мессенджера
          </p>
        </div>
        <button
          type="button"
          onClick={copy}
          className="px-4 py-2 rounded-xl bg-brand-green text-white text-sm font-medium shrink-0"
        >
          Копировать
        </button>
      </div>
      <pre className="text-xs text-slate-700 whitespace-pre-wrap bg-white/70 rounded-xl p-3 border border-emerald-100 max-h-48 overflow-y-auto">
        {message}
      </pre>
    </div>
  );
}
