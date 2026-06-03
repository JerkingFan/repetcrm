"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import Alert from "@/components/Alert";
import Whiteboard, { BoardState } from "@/components/Whiteboard";

type Board = {
  id: number;
  title: string;
  share_token: string;
  state_json: BoardState;
};

export default function PublicBoardPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const id = Number(params.id);
  const token = search.get("token") || "";

  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setError("Нет токена доступа к доске (token=...)");
      return;
    }
    api.boards
      .getPublic(id, token)
      .then((b) => setBoard(b as Board))
      .catch((e) => setError(e instanceof ApiError ? e.message : "Не удалось открыть доску"));
  }, [id, token]);

  if (!board && !error) return <LoadingSpinner label="Открываю доску..." />;

  return (
    <div className="fixed inset-0 bg-slate-50">
      {error && (
        <div className="absolute top-4 left-4 right-4 z-20">
          <Alert message={error} onClose={() => setError("")} />
        </div>
      )}
      {board && (
        <>
          <div className="absolute top-0 left-0 right-0 z-20 bg-white/90 backdrop-blur border-b border-slate-200 p-3 lg:p-4">
            <div className="max-w-[1400px] mx-auto flex items-center justify-between gap-3">
              <div>
                <h1 className="text-lg lg:text-xl font-bold text-brand-blue">{board.title || "Виртуальная доска"}</h1>
                <p className="text-slate-500 text-xs lg:text-sm mt-0.5">
                  Гостевой режим: можно писать, рисовать и вставлять картинки.
                </p>
              </div>
              <a className="text-sm text-brand-blue hover:underline" href="/login">
                Войти в CRM →
              </a>
            </div>
          </div>
          <div className="absolute inset-0 pt-[64px] lg:pt-[72px]">
            <Whiteboard boardId={board.id} shareToken={token} initialState={board.state_json} fullscreen />
          </div>
        </>
      )}
    </div>
  );
}

