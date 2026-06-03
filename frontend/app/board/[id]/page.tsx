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
        <Whiteboard boardId={board.id} shareToken={token} initialState={board.state_json} fullscreen />
      )}
    </div>
  );
}

