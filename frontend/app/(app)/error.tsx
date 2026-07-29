"use client";

import { useEffect } from "react";
import Link from "next/link";
import Alert from "@/components/Alert";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="max-w-lg mx-auto mt-16 space-y-4">
      <h1 className="text-xl font-display font-semibold text-slate-900">Что-то пошло не так</h1>
      <Alert message="Не удалось загрузить страницу. Попробуйте обновить или вернитесь позже." />
      {error.digest && (
        <p className="text-xs text-slate-500">Код ошибки: {error.digest}</p>
      )}
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={reset} className="rc-btn-primary">
          Повторить
        </button>
        <Link href="/dashboard" className="rc-btn-ink">
          На главную
        </Link>
      </div>
    </div>
  );
}
