"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { setToken } from "@/lib/auth";
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
      const { access_token } = await api.register(email, password, name);
      setToken(access_token);
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка регистрации");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-slate-50">
      <form onSubmit={submit} className="w-full max-w-md bg-white p-8 rounded-2xl shadow-lg space-y-6">
        <h1 className="text-2xl font-bold text-brand-blue">Регистрация</h1>
        {error && <Alert message={error} onClose={() => setError("")} />}
        <div>
          <label className="block text-sm font-medium mb-1">Имя</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-green/30 outline-none"
            placeholder="Как вас зовут?"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-green/30 outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Пароль (мин. 6)</label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-brand-green/30 outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-xl bg-brand-green text-white font-semibold hover:bg-emerald-600 disabled:opacity-60"
        >
          {loading ? "Создание..." : "Создать аккаунт"}
        </button>
        <p className="text-center text-sm text-slate-500">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-brand-blue font-medium hover:underline">
            Войти
          </Link>
        </p>
      </form>
    </div>
  );
}
