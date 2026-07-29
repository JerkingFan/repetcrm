"use client";

import { useEffect } from "react";
import Link from "next/link";
import Alert from "@/components/Alert";

export default function PortalError({
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
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-16 text-center">
      <h1 className="portal-title text-xl">Что-то пошло не так</h1>
      <div className="mt-4 w-full max-w-md text-left">
        <Alert message="Не удалось загрузить кабинет. Попробуйте обновить страницу." />
      </div>
      {error.digest && (
        <p className="mt-3 text-xs text-slate-500">Код ошибки: {error.digest}</p>
      )}
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <button type="button" onClick={reset} className="portal-btn-primary">
          Повторить
        </button>
        <Link href="/portal" className="portal-btn-ghost">
          В кабинет
        </Link>
      </div>
    </div>
  );
}
