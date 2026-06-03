"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/auth";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";

type Board = {
  id: number;
  title: string;
  share_token: string;
  updated_at?: string;
};

export default function BoardsPage() {
  const router = useRouter();
  const [boards, setBoards] = useState<Board[] | null>(null);
  const [title, setTitle] = useState("Виртуальная доска");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    const token = getToken();
    if (!token) return;
    const data = (await api.boards.list(token)) as Board[];
    setBoards(data);
  };

  useEffect(() => {
    load().catch(() => setBoards([]));
  }, []);

  const create = async () => {
    const token = getToken();
    if (!token) return;
    setError("");
    setCreating(true);
    try {
      const b = (await api.boards.create(token, title)) as { id: number };
      router.push(`/boards/${b.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось создать доску");
    } finally {
      setCreating(false);
    }
  };

  if (!boards) return <LoadingSpinner label="Загрузка досок..." />;

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-blue">Виртуальная доска</h1>
        <p className="text-slate-500 mt-1">Создавайте доски и делитесь ссылкой с учениками без авторизации.</p>
      </div>

      {error && <Alert message={error} onClose={() => setError("")} />}

      <div className="p-5 rounded-2xl bg-white border shadow-sm flex flex-col sm:flex-row gap-3">
        <input
          className="flex-1 px-4 py-3 rounded-xl border"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Название доски"
        />
        <button
          onClick={create}
          disabled={creating}
          className="px-5 py-3 rounded-xl bg-brand-green text-white font-semibold disabled:opacity-60"
        >
          {creating ? "Создаю…" : "Создать доску"}
        </button>
      </div>

      <div className="grid gap-3">
        {boards.length === 0 ? (
          <p className="text-slate-500">Досок пока нет — создайте первую.</p>
        ) : (
          boards.map((b) => (
            <Link
              key={b.id}
              href={`/boards/${b.id}`}
              className="p-5 rounded-2xl bg-white border shadow-sm hover:shadow-md transition"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-brand-blue">{b.title || "Виртуальная доска"}</p>
                  <p className="text-xs text-slate-500 mt-1">ID: {b.id}</p>
                </div>
                <span className="text-sm text-slate-500">Открыть →</span>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

