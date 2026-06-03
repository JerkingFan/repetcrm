"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/auth";
import LoadingSpinner from "@/components/LoadingSpinner";
import Alert from "@/components/Alert";
import Whiteboard, { BoardState } from "@/components/Whiteboard";

type Board = {
  id: number;
  title: string;
  share_token: string;
  state_json: BoardState;
};

export default function BoardPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const search = useSearchParams();
  const id = Number(params.id);
  const authToken = getToken() || undefined;
  const lessonId = Number(search.get("lesson") || "") || null;

  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace(`/login?next=${encodeURIComponent(`/boards/${id}`)}`);
      return;
    }
    let cancelled = false;
    api.boards
      .get(token, id)
      .then((b) => {
        if (!cancelled) setBoard(b as Board);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "Не удалось загрузить доску");
      });
    return () => {
      cancelled = true;
    };
  }, [id, router]);

  const shareUrl = useMemo(() => {
    if (!board || typeof window === "undefined") return "";
    const u = new URL(window.location.origin);
    u.pathname = `/board/${board.id}`;
    u.searchParams.set("token", board.share_token);
    return u.toString();
  }, [board]);

  if (!getToken() && !board && !error) {
    return <LoadingSpinner label="Перенаправление на вход…" />;
  }

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
                Ссылка — для ученика без авторизации (онлайн-режим).
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
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
                    () => alert("Ссылка скопирована"),
                    () => alert("Не удалось скопировать")
                  );
                }}
              >
                Копировать
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

          <div className="absolute inset-0 pt-[76px] lg:pt-[84px]">
            <Whiteboard
              boardId={board.id}
              shareToken={board.share_token}
              authToken={authToken}
              initialState={board.state_json}
              fullscreen
            />
          </div>
        </>
      )}
    </div>
  );
}

