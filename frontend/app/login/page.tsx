"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { setToken } from "@/lib/auth";
import Alert from "@/components/Alert";

const QUOTES = [
  "«Наконец-то я вижу, кто и сколько мне должен. За первый месяц вернула 400 Br пропущенных оплат»",
  "«Домашки, на которые уходил час, теперь делаю за минуту. Ученики в восторге, а я не выгораю»",
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const quote = QUOTES[Math.floor(Math.random() * QUOTES.length)];

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      const user = await api.me(access_token);
      router.push(user.onboarding_completed ? "/dashboard" : "/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-center bg-brand-blue text-white p-12">
        <h2 className="text-2xl font-bold">RepetCRM</h2>
        <p className="mt-4 text-blue-100 max-w-md">
          Учёт занятий, оплат и персональные домашки с AI за минуту
        </p>
        <blockquote className="mt-12 p-6 rounded-2xl bg-white/10 border border-white/20 italic text-blue-50">
          {quote}
        </blockquote>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-md space-y-6">
          <h1 className="text-2xl font-bold text-brand-blue">Вход</h1>
          {error && <Alert message={error} onClose={() => setError("")} />}
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
          <div>
            <label className="block text-sm font-medium mb-1">Пароль</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-green/30 focus:border-brand-green outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600 disabled:opacity-60 transition"
          >
            {loading ? "Вход..." : "Войти"}
          </button>
          <p className="text-center text-sm text-slate-500">
            Нет аккаунта?{" "}
            <Link href="/register" className="text-brand-blue font-medium hover:underline">
              Регистрация
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
