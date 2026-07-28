"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";

type SpeechRec = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((ev: { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null;
  onerror: ((ev: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

declare global {
  interface Window {
    webkitSpeechRecognition?: new () => SpeechRec;
    SpeechRecognition?: new () => SpeechRec;
  }
}

/** Hold / tap to dictate brief → save prefs + start HW generation. */
export default function VoiceBriefButton({
  lessonId,
  onStarted,
  onError,
}: {
  lessonId: number;
  onStarted?: (jobId: string | null, brief: string) => void;
  onError?: (msg: string) => void;
}) {
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [supported, setSupported] = useState(true);
  const recRef = useRef<SpeechRec | null>(null);

  useEffect(() => {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    setSupported(!!Ctor);
  }, []);

  const startListen = () => {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) {
      setSupported(false);
      return;
    }
    const rec = new Ctor();
    rec.lang = "ru-RU";
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (ev) => {
      let text = "";
      for (let i = 0; i < ev.results.length; i++) {
        text += ev.results[i][0].transcript + " ";
      }
      setDraft(text.trim());
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const stopListen = () => {
    recRef.current?.stop();
    setListening(false);
  };

  const submit = async () => {
    const brief = draft.trim();
    if (brief.length < 3) {
      onError?.("Скажите или введите хотя бы пару слов");
      return;
    }
    setBusy(true);
    try {
      const res = await api.lessons.voiceBrief(lessonId, brief, true);
      onStarted?.(res.job_id || null, res.brief);
      setDraft("");
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : "Не удалось запустить генерацию");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4 p-4 rounded-2xl border border-violet-200 bg-violet-50/80 space-y-3">
      <div>
        <p className="text-sm font-semibold text-violet-950">Голос → ДЗ</p>
        <p className="text-xs text-violet-800/80 mt-0.5">
          Надиктуй 10–20 сек: «слабые логарифмы, 4 задачи» — AI соберёт домашку
        </p>
      </div>
      {!supported && (
        <p className="text-xs text-amber-800">
          Голос в этом браузере недоступен — введи текст вручную (Chrome на телефоне/ПК удобнее).
        </p>
      )}
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={2}
        placeholder="Или вставь текст брифа…"
        className="w-full px-3 py-2 rounded-xl border border-violet-200 bg-white text-sm"
      />
      <div className="flex flex-wrap gap-2">
        {supported && (
          <button
            type="button"
            onClick={() => (listening ? stopListen() : startListen())}
            className={`px-4 py-2.5 rounded-xl text-sm font-semibold ${
              listening ? "bg-rose-500 text-white animate-pulse" : "bg-white border border-violet-200 text-violet-900"
            }`}
          >
            {listening ? "⏹ Стоп" : "🎤 Диктовать"}
          </button>
        )}
        <button
          type="button"
          disabled={busy || draft.trim().length < 3}
          onClick={submit}
          className="px-4 py-2.5 rounded-xl bg-violet-600 text-white text-sm font-semibold disabled:opacity-50"
        >
          {busy ? "Запуск…" : "Сгенерировать ДЗ"}
        </button>
      </div>
    </div>
  );
}
