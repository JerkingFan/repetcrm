"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { clearLegacyToken } from "@/lib/auth";
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
  const [quote, setQuote] = useState(QUOTES[0]);

  useEffect(() => {
    setQuote(QUOTES[Math.floor(Math.random() * QUOTES.length)]);
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.login(email, password);
      clearLegacyToken();
      const user = await api.me();
      router.push(user.onboarding_completed ? "/dashboard" : "/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-ink-hero text-white p-12 xl:p-16">
        <div
          className="pointer-events-none absolute -top-24 -right-16 w-80 h-80 rounded-full bg-teal-300/25 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute bottom-10 left-0 w-72 h-72 rounded-full bg-cyan-400/20 blur-3xl"
          aria-hidden
        />
        <div className="relative">
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-teal-100/70">
            RepetCRM
          </p>
          <h2 className="mt-4 font-display text-4xl xl:text-5xl font-bold tracking-tight leading-[1.05] max-w-lg">
            Практика без хаоса
          </h2>
          <p className="mt-4 text-teal-50/85 max-w-md text-base leading-relaxed">
            Учёт занятий, оплат и персональные домашки с AI — за минуту, а не за вечер.
          </p>
        </div>
        <blockquote className="relative mt-12 p-6 rounded-2xl bg-white/10 border border-white/15 backdrop-blur-sm text-teal-50/95 leading-relaxed">
          {quote}
        </blockquote>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10 bg-app-mesh">
        <form onSubmit={submit} className="w-full max-w-md space-y-6 rc-card-pad shadow-lift">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-brand-blue/70 lg:hidden">
              RepetCRM
            </p>
            <h1 className="rc-page-title mt-1">Вход</h1>
            <p className="rc-page-sub">В кабинет репетитора</p>
          </div>
          {error && <Alert message={error} onClose={() => setError("")} />}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rc-input"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-semibold text-slate-700">Пароль</label>
              <Link href="/forgot-password" className="text-sm font-semibold text-brand-blue hover:underline">
                Забыли пароль?
              </Link>
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rc-input"
            />
          </div>
          <button type="submit" disabled={loading} className="rc-btn-primary w-full !py-3">
            {loading ? "Вход..." : "Войти"}
          </button>
          <p className="text-center text-sm text-slate-500">
            Нет аккаунта?{" "}
            <Link href="/register" className="text-brand-blue font-bold hover:underline">
              Регистрация
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
