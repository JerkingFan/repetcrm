"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import Alert from "@/components/Alert";

function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!token) {
      setError("Ссылка недействительна — нет токена");
      return;
    }
    if (password !== confirm) {
      setError("Пароли не совпадают");
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword(token, password);
      router.push("/login?reset=1");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка сброса");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md space-y-6">
      <h1 className="text-2xl font-bold text-brand-blue">Новый пароль</h1>
      {!token && (
        <Alert message="Ссылка недействительна. Запросите сброс пароля заново." />
      )}
      {error && <Alert message={error} onClose={() => setError("")} />}
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Новый пароль</label>
          <input
            type="password"
            required
            minLength={10}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-green/30 focus:border-brand-green outline-none"
          />
          <p className="text-xs text-slate-400 mt-1">Минимум 10 символов</p>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Повторите пароль</label>
          <input
            type="password"
            required
            minLength={10}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-green/30 focus:border-brand-green outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !token}
          className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600 disabled:opacity-60"
        >
          {loading ? "Сохранение…" : "Сохранить пароль"}
        </button>
      </form>
      <p className="text-center text-sm text-slate-500">
        <Link href="/forgot-password" className="text-brand-blue font-medium hover:underline">
          Запросить новую ссылку
        </Link>
      </p>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <Suspense fallback={<p className="text-slate-500">Загрузка…</p>}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
