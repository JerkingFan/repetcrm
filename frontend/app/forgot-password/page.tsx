"use client";

import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import Alert from "@/components/Alert";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка запроса");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6">
        <h1 className="text-2xl font-bold text-brand-blue">Забыли пароль?</h1>
        <p className="text-sm text-slate-500">
          Введите email — если аккаунт есть, пришлём ссылку для сброса пароля.
        </p>
        {error && <Alert message={error} onClose={() => setError("")} />}
        {sent ? (
          <Alert
            type="success"
            message="Если email зарегистрирован, письмо уже отправлено. Проверьте почту (и папку «Спам»)."
          />
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-green/30 focus:border-brand-green outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600 disabled:opacity-60"
            >
              {loading ? "Отправка…" : "Отправить ссылку"}
            </button>
          </form>
        )}
        <p className="text-center text-sm text-slate-500">
          <Link href="/login" className="text-brand-blue font-medium hover:underline">
            ← Вернуться ко входу
          </Link>
        </p>
      </div>
    </div>
  );
}
