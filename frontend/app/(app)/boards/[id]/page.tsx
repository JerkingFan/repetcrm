"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import Alert from "@/components/Alert";
import Whiteboard, { BoardState } from "@/components/Whiteboard";
import { toast } from "@/lib/toast";

type Board = {
  id: number;
  title: string;
  share_token: string;
  share_writable: boolean;
  state_json: BoardState;
};

export default function BoardPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const id = Number(params.id);
  const lessonId = Number(search.get("lesson") || "") || null;

  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState("");
  const [snapshots, setSnapshots] = useState<Array<{ id: number; created_at: string }>>([]);
  const [stateKey, setStateKey] = useState(0);
  const [showSnapshots, setShowSnapshots] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.boards
      .get(id)
      .then((b) => {
        if (!cancelled) setBoard(b as Board);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "Не удалось загрузить доску");
      });
    api.boards.listSnapshots(id).then((s) => {
      if (!cancelled) setSnapshots(s);
    });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const restoreSnapshot = async (snapshotId: number) => {
    if (!confirm("Восстановить доску из этого снимка? Текущее состояние будет заменено.")) return;
    try {
      const restored = (await api.boards.restoreSnapshot(id, snapshotId)) as Board;
      setBoard(restored);
      setStateKey((k) => k + 1);
      toast("Доска восстановлена из снимка", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Ошибка восстановления", "error");
    }
  };

  const shareUrl = useMemo(() => {
    if (!board || typeof window === "undefined") return "";
    const u = new URL(window.location.origin);
    u.pathname = `/board/${board.id}`;
    u.searchParams.set("token", board.share_token);
    return u.toString();
  }, [board]);

  if (!board && !error) return <LoadingSpinner label="Загрузка доски..." />;

  return (
    <div className="fixed inset-0 bg-slate-50">
      {error && <Alert message={error} onClose={() => setError("")} />}
      {board && (
        <>
          <div className="absolute top-0 left-0 right-0 z-20 bg-white/90 backdrop-blur border-b border-slate-200 p-3 lg:p-4">
            <div className="max-w-[1400px] mx-auto flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
            <div>
              <h1 className="text-lg lg:text-xl font-bold text-brand-blue">{board.title || "Виртуальная доска"}</h1>
              <p className="text-slate-500 text-xs lg:text-sm mt-0.5">
                Ссылка — для ученика без авторизации. Рисование по ссылке можно включить отдельно.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
              <label className="flex items-center gap-2 text-sm text-slate-700 px-2">
                <input
                  type="checkbox"
                  checked={board.share_writable}
                  onChange={async (e) => {
                    const share_writable = e.target.checked;
                    try {
                      const updated = (await api.boards.update(id, { share_writable })) as Board;
                      setBoard(updated);
                      toast(
                        share_writable
                          ? "Ученик может рисовать по ссылке"
                          : "Ученик только смотрит (read-only)",
                        "success"
                      );
                    } catch (err) {
                      toast(err instanceof ApiError ? err.message : "Не удалось сохранить", "error");
                    }
                  }}
                />
                Ученик может рисовать
              </label>
              {lessonId ? (
                <a
                  className="px-4 py-2.5 rounded-xl bg-brand-green text-white font-semibold text-sm text-center"
                  href={`/lessons/${lessonId}#after-lesson`}
                >
                  Занятие закончилось? В чек-лист →
                </a>
              ) : null}
              <input
                className="px-3 py-2.5 rounded-xl border w-full sm:w-[26rem] text-sm"
                readOnly
                value={shareUrl}
              />
              <button
                className="px-4 py-2.5 rounded-xl bg-slate-900 text-white font-semibold text-sm"
                onClick={() => {
                  if (!shareUrl) return;
                  navigator.clipboard.writeText(shareUrl).then(
                    () => toast("Ссылка скопирована", "success"),
                    () => toast("Не удалось скопировать", "error")
                  );
                }}
              >
                Копировать
              </button>
              <button
                type="button"
                className="px-4 py-2.5 rounded-xl border bg-white font-semibold text-sm"
                onClick={() => setShowSnapshots((v) => !v)}
              >
                Снимки ({snapshots.length})
              </button>
              <a
                className="px-4 py-2.5 rounded-xl border bg-white font-semibold text-center text-sm"
                href={shareUrl}
                target="_blank"
                rel="noreferrer"
              >
                Открыть →
              </a>
            </div>
          </div>
          </div>

          {showSnapshots && (
            <div className="absolute top-[76px] lg:top-[84px] right-4 z-30 w-72 max-h-[50vh] overflow-y-auto p-4 rounded-2xl bg-white border shadow-lg">
              <p className="text-sm font-semibold text-brand-blue mb-2">Восстановление</p>
              {snapshots.length === 0 ? (
                <p className="text-xs text-slate-500">Снимков пока нет</p>
              ) : (
                <ul className="space-y-2">
                  {snapshots.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        onClick={() => restoreSnapshot(s.id)}
                        className="w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 border border-slate-100"
                      >
                        {new Date(s.created_at).toLocaleString("ru-RU")}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="absolute inset-0 pt-[76px] lg:pt-[84px]">
            <Whiteboard
              key={stateKey}
              boardId={board.id}
              shareToken={board.share_token}
              connectAsGuest={false}
              initialState={board.state_json}
              fullscreen
            />
          </div>
        </>
      )}
    </div>
  );
}
