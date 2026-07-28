"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { clearLegacyToken } from "@/lib/auth";
import Alert from "@/components/Alert";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.register(email, password, name);
      clearLegacyToken();
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка регистрации");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-app-mesh">
      <form onSubmit={submit} className="w-full max-w-md space-y-5 rc-card-pad shadow-lift">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-brand-blue/70">
            RepetCRM
          </p>
          <h1 className="rc-page-title mt-1">Регистрация</h1>
          <p className="rc-page-sub">Создай кабинет репетитора за минуту</p>
        </div>
        {error && <Alert message={error} onClose={() => setError("")} />}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-1.5">Имя</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rc-input"
            placeholder="Как вас зовут?"
          />
        </div>
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
          <label className="block text-sm font-semibold text-slate-700 mb-1.5">
            Пароль (мин. 10, буква и цифра)
          </label>
          <input
            type="password"
            required
            minLength={10}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rc-input"
          />
        </div>
        <button type="submit" disabled={loading} className="rc-btn-primary w-full !py-3">
          {loading ? "Создание..." : "Создать аккаунт"}
        </button>
        <p className="text-center text-sm text-slate-500">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-brand-blue font-bold hover:underline">
            Войти
          </Link>
        </p>
      </form>
    </div>
  );
}
