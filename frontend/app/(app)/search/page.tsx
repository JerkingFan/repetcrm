"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import Alert from "@/components/Alert";
import Skeleton from "@/components/Skeleton";
import { api, ApiError, type GlobalSearchOut } from "@/lib/api";

export default function GlobalSearchPage() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") || "";

  const [draft, setDraft] = useState(q);
  const [data, setData] = useState<GlobalSearchOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setDraft(q);
  }, [q]);

  useEffect(() => {
    if (!q.trim()) return;
    setLoading(true);
    setError("");
    api
      .search.global(q)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Не удалось выполнить поиск"))
      .finally(() => setLoading(false));
  }, [q]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const next = draft.trim();
    if (!next) {
      router.push("/search");
      return;
    }
    router.push(`/search?q=${encodeURIComponent(next)}`);
  };

  return (
    <div className="max-w-4xl">
      <h1 className="rc-page-title">Поиск</h1>
      <p className="rc-page-sub">Ученики и занятия по вашему запросу</p>

      <form onSubmit={submit} className="mt-6 flex flex-wrap gap-3 items-center">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Например: Иванов или 16:00"
          className="rc-input flex-1 min-w-[240px]"
        />
        <button type="submit" className="rc-btn-primary !py-3">
          Найти
        </button>
      </form>

      {error && <div className="mt-4"><Alert message={error} onClose={() => setError("")} /></div>}

      {!q.trim() && (
        <p className="mt-10 text-sm text-slate-500">Введите запрос, чтобы начать поиск.</p>
      )}

      {loading && q.trim() && (
        <div className="mt-8 space-y-6">
          <div className="space-y-3">
            <Skeleton className="h-5 w-44" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-5 w-44" />
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        </div>
      )}

      {!loading && data && (
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <section className="space-y-3">
            <h2 className="font-semibold text-brand-blue">Ученики</h2>
            {data.students.length === 0 ? (
              <p className="text-sm text-slate-500">Ничего не найдено</p>
            ) : (
              <ul className="space-y-2">
                {data.students.map((s) => (
                  <li key={s.id}>
                    <Link
                      href={`/students/${s.id}`}
                      className="block p-3 rounded-xl border border-slate-100 hover:bg-slate-50 transition"
                    >
                      <div className="font-semibold text-sm text-brand-blue">{s.name}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {s.grade ? `${s.grade}` : ""}{s.subject ? ` · ${s.subject}` : ""}{s.school ? ` · ${s.school}` : ""}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="font-semibold text-brand-blue">Занятия</h2>
            {data.lessons.length === 0 ? (
              <p className="text-sm text-slate-500">Ничего не найдено</p>
            ) : (
              <ul className="space-y-2">
                {data.lessons.map((l) => (
                  <li key={l.id}>
                    <Link
                      href={`/lessons/${l.id}`}
                      className="block p-3 rounded-xl border border-slate-100 hover:bg-slate-50 transition"
                    >
                      <div className="font-semibold text-sm text-brand-blue">
                        {l.student_name || "Ученик"}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {l.lesson_date} · {l.lesson_time} · {l.is_paid ? "оплачено" : "не оплачено"}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

