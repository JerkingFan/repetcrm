"use client";

import { useEffect, useRef, useState } from "react";
import { formatRuDate } from "@/lib/portalUi";
import { formatLessonTime } from "@/lib/calendar";

type Hw = {
  id: number;
  lesson_date: string;
  preview: string;
  due_date?: string | null;
  submission_status?: string;
  has_submission: boolean;
};

type Lesson = {
  id: number;
  lesson_date: string;
  lesson_time: string;
  board_url?: string;
  meeting_url?: string;
  is_conducted: boolean;
};

/** Lo-fi focus room: quiet UI + optional ambient audio + tasks/board. */
export default function PortalFocus({
  open,
  onClose,
  homework,
  lessons,
  onOpenHomework,
}: {
  open: boolean;
  onClose: () => void;
  homework: Hw[];
  lessons: Lesson[];
  onOpenHomework: (id: number) => void;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [musicOn, setMusicOn] = useState(false);
  const [started, setStarted] = useState(false);

  const todos = homework.filter(
    (h) => !h.has_submission || h.submission_status === "needs_revision"
  );
  const boardLesson =
    lessons.find((l) => !l.is_conducted && l.board_url) ||
    lessons.find((l) => l.board_url) ||
    null;

  useEffect(() => {
    if (!open) {
      setMusicOn(false);
      setStarted(false);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    }
  }, [open]);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    if (musicOn) {
      el.volume = 0.28;
      el.play().catch(() => setMusicOn(false));
    } else {
      el.pause();
    }
  }, [musicOn]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-[#0b1220] text-slate-100 overflow-y-auto">
      {/* Soft ambient gradient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_#1e3a5f_0%,_transparent_55%),radial-gradient(ellipse_at_bottom,_#0f766e22_0%,_transparent_50%)]" />

      <audio
        ref={audioRef}
        loop
        preload="none"
        src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3"
      />

      <div className="relative max-w-lg mx-auto px-4 pt-6 pb-16 space-y-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-teal-300/80 font-semibold">
              Режим фокуса
            </p>
            <h2 className="text-2xl font-bold mt-1 tracking-tight">Тихо. Только задачи.</h2>
            <p className="text-sm text-slate-400 mt-1">Доска, ДЗ и лёгкий lo-fi — без отвлечений</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 rounded-xl border border-white/15 text-sm text-slate-300 hover:bg-white/5"
          >
            Выйти
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              setStarted(true);
              setMusicOn((v) => !v);
            }}
            className={`px-4 py-2.5 rounded-xl text-sm font-semibold transition ${
              musicOn ? "bg-teal-500 text-white" : "bg-white/10 text-slate-200 border border-white/10"
            }`}
          >
            {musicOn ? "Музыка ▶" : "Lo-fi ▶"}
          </button>
          {boardLesson?.board_url && (
            <a
              href={boardLesson.board_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2.5 rounded-xl bg-white/10 border border-white/10 text-sm font-semibold"
            >
              Открыть доску
            </a>
          )}
          {boardLesson?.meeting_url && (
            <a
              href={boardLesson.meeting_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2.5 rounded-xl bg-emerald-500/90 text-white text-sm font-semibold"
            >
              Войти в урок
            </a>
          )}
        </div>

        {!started && (
          <p className="text-xs text-slate-500">
            Нажми Lo-fi, чтобы включить фоновый трек (можно и без музыки).
          </p>
        )}

        <section className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
          <h3 className="font-semibold text-slate-100 mb-3">Задания сейчас</h3>
          {todos.length === 0 ? (
            <p className="text-sm text-slate-400">Всё сдано — можно просто открыть доску и повторить.</p>
          ) : (
            <ul className="space-y-2">
              {todos.slice(0, 6).map((h, i) => (
                <li key={h.id} className="portal-focus-item" style={{ animationDelay: `${i * 60}ms` }}>
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      onOpenHomework(h.id);
                    }}
                    className="w-full text-left rounded-xl border border-white/10 bg-black/20 px-3 py-3 hover:border-teal-400/40 transition"
                  >
                    <p className="text-sm font-medium">{formatRuDate(h.lesson_date)}</p>
                    {h.preview && (
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">{h.preview}</p>
                    )}
                    <p className="text-[11px] font-semibold text-teal-300 mt-2">Решать →</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {boardLesson && (
          <p className="text-xs text-slate-500 text-center">
            Ближайший урок: {formatRuDate(boardLesson.lesson_date)} ·{" "}
            {formatLessonTime(boardLesson.lesson_time)}
          </p>
        )}
      </div>
    </div>
  );
}
