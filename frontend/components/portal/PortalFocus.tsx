"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import {
  AI_VERDICT_LABEL,
  formatRuDate,
  homeworkDueLabel,
  SUBMISSION_STATUS_LABEL,
} from "@/lib/portalUi";

type Hw = {
  id: number;
  lesson_date: string;
  preview: string;
  due_date?: string | null;
  submission_status?: string;
  has_submission: boolean;
};

type Detail = Awaited<ReturnType<typeof api.portal.homeworkDetail>>;

/** Soft study lo-fi via Web Audio (vinyl + pad + beat). */
class LofiEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private nodes: AudioNode[] = [];
  private timers: number[] = [];
  private playing = false;

  async start() {
    if (this.playing) return;
    const Ctx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.ctx = new Ctx();
    if (this.ctx.state === "suspended") await this.ctx.resume();
    this.master = this.ctx.createGain();
    this.master.gain.value = 0.22;
    this.master.connect(this.ctx.destination);
    this._vinyl();
    this._pad();
    this._beat();
    this.playing = true;
  }

  stop() {
    this.playing = false;
    for (const t of this.timers) window.clearInterval(t);
    this.timers = [];
    for (const n of this.nodes) {
      try {
        n.disconnect();
      } catch {
        /* ignore */
      }
    }
    this.nodes = [];
    if (this.ctx) {
      void this.ctx.close().catch(() => {});
      this.ctx = null;
    }
    this.master = null;
  }

  setVolume(v: number) {
    if (this.master) this.master.gain.value = Math.max(0, Math.min(0.45, v));
  }

  private _vinyl() {
    const ctx = this.ctx!;
    const master = this.master!;
    const bufferSize = 2 * ctx.sampleRate;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      const noise = Math.random() * 2 - 1;
      const pop = Math.random() > 0.997 ? (Math.random() * 2 - 1) * 0.35 : 0;
      data[i] = noise * 0.018 + pop;
    }
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 1800;
    filter.Q.value = 0.6;
    const g = ctx.createGain();
    g.gain.value = 0.55;
    src.connect(filter);
    filter.connect(g);
    g.connect(master);
    src.start();
    this.nodes.push(src, filter, g);
  }

  private _pad() {
    const ctx = this.ctx!;
    const master = this.master!;
    const chords = [
      [220.0, 261.63, 329.63, 392.0],
      [146.83, 174.61, 220.0, 349.23],
      [196.0, 246.94, 293.66, 349.23],
      [130.81, 164.81, 196.0, 261.63],
    ];
    let idx = 0;
    const playChord = () => {
      if (!this.playing || !this.ctx) return;
      const freqs = chords[idx % chords.length];
      idx += 1;
      const now = ctx.currentTime;
      const chordGain = ctx.createGain();
      chordGain.gain.setValueAtTime(0, now);
      chordGain.gain.linearRampToValueAtTime(0.07, now + 0.8);
      chordGain.gain.linearRampToValueAtTime(0.045, now + 3.5);
      chordGain.gain.linearRampToValueAtTime(0.001, now + 7.2);
      chordGain.connect(master);
      this.nodes.push(chordGain);
      for (const f of freqs) {
        const osc = ctx.createOscillator();
        osc.type = "triangle";
        osc.frequency.value = f * 0.5;
        const detune = ctx.createOscillator();
        detune.type = "sine";
        detune.frequency.value = f * 0.5 * 1.003;
        const mix = ctx.createGain();
        mix.gain.value = 0.5;
        const lp = ctx.createBiquadFilter();
        lp.type = "lowpass";
        lp.frequency.value = 900;
        osc.connect(mix);
        detune.connect(mix);
        mix.connect(lp);
        lp.connect(chordGain);
        osc.start(now);
        detune.start(now);
        osc.stop(now + 7.4);
        detune.stop(now + 7.4);
      }
    };
    playChord();
    this.timers.push(window.setInterval(playChord, 7200));
  }

  private _beat() {
    const ctx = this.ctx!;
    const master = this.master!;
    const bpm = 76;
    const stepMs = 60_000 / bpm / 2;
    let step = 0;

    const kick = () => {
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.frequency.setValueAtTime(110, now);
      osc.frequency.exponentialRampToValueAtTime(42, now + 0.18);
      g.gain.setValueAtTime(0.22, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
      osc.connect(g);
      g.connect(master);
      osc.start(now);
      osc.stop(now + 0.3);
    };

    const snare = () => {
      const now = ctx.currentTime;
      const bufferSize = Math.floor(ctx.sampleRate * 0.12);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const bp = ctx.createBiquadFilter();
      bp.type = "bandpass";
      bp.frequency.value = 1800;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.12, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
      src.connect(bp);
      bp.connect(g);
      g.connect(master);
      src.start(now);
    };

    const hat = () => {
      const now = ctx.currentTime;
      const bufferSize = Math.floor(ctx.sampleRate * 0.04);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const hp = ctx.createBiquadFilter();
      hp.type = "highpass";
      hp.frequency.value = 7000;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.035, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
      src.connect(hp);
      hp.connect(g);
      g.connect(master);
      src.start(now);
    };

    const tick = () => {
      if (!this.playing || !this.ctx) return;
      const s = step % 8;
      if (s === 0 || s === 4) kick();
      if (s === 2 || s === 6) snare();
      if (s % 2 === 1) hat();
      step += 1;
    };
    tick();
    this.timers.push(window.setInterval(tick, stepMs));
  }
}

function resultTone(verdict?: string): string {
  switch (verdict) {
    case "correct":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
    case "partially_correct":
      return "border-amber-500/40 bg-amber-500/10 text-amber-100";
    case "incorrect":
      return "border-rose-500/40 bg-rose-500/10 text-rose-100";
    default:
      return "border-white/10 bg-white/5 text-slate-200";
  }
}

export default function PortalFocus({
  open,
  onClose,
  homework,
  onSubmitted,
}: {
  open: boolean;
  onClose: () => void;
  homework: Hw[];
  onSubmitted?: () => void;
}) {
  const engineRef = useRef<LofiEngine | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const todos = homework.filter(
    (h) => !h.has_submission || h.submission_status === "needs_revision"
  );

  const [activeId, setActiveId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(false);
  const [comment, setComment] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [musicOn, setMusicOn] = useState(false);
  const [volume, setVolume] = useState(0.22);
  const [lofiOpen, setLofiOpen] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);
  const [resultOpen, setResultOpen] = useState(true);

  useEffect(() => {
    if (!open) {
      setMusicOn(false);
      engineRef.current?.stop();
      engineRef.current = null;
      setActiveId(null);
      setDetail(null);
      setComment("");
      setError("");
      setLofiOpen(false);
      setDescExpanded(false);
      return;
    }
    const first = todos[0]?.id ?? homework[0]?.id ?? null;
    setActiveId(first);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps -- init once on open

  useEffect(() => {
    return () => {
      engineRef.current?.stop();
      engineRef.current = null;
    };
  }, []);

  useEffect(() => {
    engineRef.current?.setVolume(volume);
  }, [volume]);

  useEffect(() => {
    if (!open || !activeId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    setDescExpanded(false);
    api.portal
      .homeworkDetail(activeId)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null);
          setError("Не удалось загрузить задание");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, activeId]);

  // Poll AI review
  useEffect(() => {
    if (!open || !activeId || !detail) return;
    const needs = detail.submissions.some(
      (s) => s.ai_review_status === "pending" || s.ai_review_status === "running"
    );
    if (!needs) return;
    const t = setInterval(() => {
      api.portal.homeworkDetail(activeId).then(setDetail).catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [open, activeId, detail]);

  const toggleMusic = async () => {
    if (musicOn) {
      engineRef.current?.stop();
      engineRef.current = null;
      setMusicOn(false);
      return;
    }
    const eng = new LofiEngine();
    engineRef.current = eng;
    try {
      await eng.start();
      eng.setVolume(volume);
      setMusicOn(true);
    } catch {
      engineRef.current = null;
      setMusicOn(false);
    }
  };

  const exit = () => {
    engineRef.current?.stop();
    engineRef.current = null;
    onClose();
  };

  const submitFile = async (file: File) => {
    if (!activeId) return;
    setUploading(true);
    setError("");
    try {
      await api.portal.submitHomework(activeId, file, comment);
      setComment("");
      setResultOpen(true);
      const d = await api.portal.homeworkDetail(activeId);
      setDetail(d);
      onSubmitted?.();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка загрузки");
    } finally {
      setUploading(false);
    }
  };

  if (!open) return null;

  const latest = detail?.submissions[0];
  const status = latest?.status || (detail ? "not_submitted" : "");
  const due = detail ? homeworkDueLabel(detail.due_date, detail.lesson_date) : null;
  const list = todos.length > 0 ? todos : homework;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#1a1a1a] text-slate-100">
      {/* Top bar — LeetCode-ish */}
      <header className="shrink-0 h-12 border-b border-white/10 bg-[#282828] flex items-center gap-2 px-3">
        <button
          type="button"
          onClick={exit}
          className="px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-300 hover:bg-white/10"
        >
          ← Выйти
        </button>
        <div className="h-4 w-px bg-white/10" />
        <p className="text-xs font-semibold tracking-wide text-slate-300 uppercase">Фокус</p>
        <div className="flex-1 min-w-0 overflow-x-auto flex items-center gap-1.5 px-2">
          {list.map((h) => {
            const active = h.id === activeId;
            return (
              <button
                key={h.id}
                type="button"
                onClick={() => setActiveId(h.id)}
                className={`shrink-0 px-2.5 py-1 rounded-md text-xs font-medium transition ${
                  active
                    ? "bg-[#3a3a3a] text-white border border-white/15"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`}
              >
                {formatRuDate(h.lesson_date, { day: "numeric", month: "short" })}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={toggleMusic}
          className={`shrink-0 px-2.5 py-1.5 rounded-md text-xs font-semibold ${
            musicOn ? "bg-teal-600 text-white" : "text-slate-300 hover:bg-white/10"
          }`}
        >
          {musicOn ? "Lo-fi ●" : "Lo-fi"}
        </button>
      </header>

      {/* Main split */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
        {/* Left — problem */}
        <section className="flex-1 min-h-0 lg:w-1/2 lg:border-r border-white/10 flex flex-col bg-[#1a1a1a]">
          <div className="shrink-0 px-4 py-3 border-b border-white/10 bg-[#222]">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">
                  Задание
                </p>
                <h2 className="text-base font-semibold text-white truncate">
                  {detail
                    ? formatRuDate(detail.lesson_date, {
                        day: "numeric",
                        month: "long",
                        weekday: "short",
                      })
                    : "Задание"}
                </h2>
                {due && (
                  <p className={`text-xs mt-0.5 ${due.urgent ? "text-rose-300" : "text-slate-500"}`}>
                    {due.text}
                  </p>
                )}
              </div>
              {status && (
                <span className="text-[10px] font-semibold px-2 py-1 rounded bg-white/10 text-slate-300 shrink-0">
                  {SUBMISSION_STATUS_LABEL[status] || status}
                </span>
              )}
            </div>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4">
            {loading && <p className="text-sm text-slate-500">Загрузка…</p>}
            {!loading && !detail && list.length === 0 && (
              <p className="text-sm text-slate-500">Нет заданий — можно просто слушать lo-fi.</p>
            )}
            {!loading && detail && (
              <>
                <div
                  className={`portal-hw-focus overflow-hidden ${
                    descExpanded ? "" : "max-h-[42vh] lg:max-h-none"
                  }`}
                >
                  <div
                    dangerouslySetInnerHTML={{
                      __html: detail.preview_html || detail.homework_text,
                    }}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setDescExpanded((v) => !v)}
                  className="mt-3 text-xs font-semibold text-teal-400 lg:hidden"
                >
                  {descExpanded ? "Свернуть" : "Показать полностью ▾"}
                </button>
                {(detail.board_url || detail.meeting_url) && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {detail.board_url && (
                      <a
                        href={detail.board_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 rounded-md border border-white/15 text-xs font-semibold text-slate-200 hover:bg-white/5"
                      >
                        Доска
                      </a>
                    )}
                    {detail.meeting_url && (
                      <a
                        href={detail.meeting_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 rounded-md bg-emerald-600 text-xs font-semibold text-white"
                      >
                        В урок
                      </a>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </section>

        {/* Right — submit */}
        <section className="shrink-0 lg:flex-1 lg:min-h-0 lg:w-1/2 flex flex-col border-t lg:border-t-0 border-white/10 bg-[#1e1e1e]">
          <div className="shrink-0 px-4 py-3 border-b border-white/10 bg-[#222]">
            <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">
              Сдача
            </p>
            <h3 className="text-sm font-semibold text-white">Сдать решение</h3>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
            {!detail ? (
              <p className="text-sm text-slate-500">Выбери задание сверху.</p>
            ) : (
              <>
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    const f = e.dataTransfer.files?.[0];
                    if (f) void submitFile(f);
                  }}
                  className={`rounded-lg border-2 border-dashed px-4 py-8 text-center transition ${
                    dragOver
                      ? "border-teal-400 bg-teal-500/10"
                      : "border-white/15 bg-black/20"
                  }`}
                >
                  <p className="text-sm text-slate-300 font-medium">Перетащи файл сюда</p>
                  <p className="text-xs text-slate-500 mt-1">PDF, фото, документ</p>
                  <div className="mt-4 flex flex-wrap justify-center gap-2">
                    <button
                      type="button"
                      disabled={uploading}
                      onClick={() => fileRef.current?.click()}
                      className="px-3 py-2 rounded-md bg-[#ffa116] text-[#1a1a1a] text-xs font-bold disabled:opacity-50"
                    >
                      {uploading ? "…" : "Выбрать файл"}
                    </button>
                    <button
                      type="button"
                      disabled={uploading}
                      onClick={() => cameraRef.current?.click()}
                      className="px-3 py-2 rounded-md border border-white/15 text-xs font-semibold text-slate-200 disabled:opacity-50"
                    >
                      Камера
                    </button>
                  </div>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*,.pdf,.doc,.docx"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void submitFile(f);
                      e.target.value = "";
                    }}
                  />
                  <input
                    ref={cameraRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) void submitFile(f);
                      e.target.value = "";
                    }}
                  />
                </div>

                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Комментарий к решению (необязательно)"
                  className="w-full min-h-[72px] rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-teal-500/50"
                />

                {error && <p className="text-xs text-rose-400">{error}</p>}

                {latest && (
                  <p className="text-xs text-slate-500">
                    Последний файл: {latest.original_filename} ·{" "}
                    {new Date(latest.submitted_at).toLocaleString("ru-RU", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                )}
              </>
            )}
          </div>
        </section>
      </div>

      {/* Bottom — result + lo-fi */}
      <footer className="shrink-0 border-t border-white/10 bg-[#282828]">
        <div className="flex items-stretch">
          <button
            type="button"
            onClick={() => setResultOpen((v) => !v)}
            className="flex-1 min-w-0 px-4 py-2.5 text-left hover:bg-white/5"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">
                Результат {resultOpen ? "▾" : "▸"}
              </p>
              {latest?.ai_review_status === "done" && latest.ai_verdict && (
                <span className="text-xs font-semibold text-slate-200 truncate">
                  {AI_VERDICT_LABEL[latest.ai_verdict] || latest.ai_verdict}
                  {latest.ai_score != null && latest.ai_verdict !== "unclear"
                    ? ` · ${latest.ai_score}%`
                    : ""}
                </span>
              )}
              {(latest?.ai_review_status === "pending" ||
                latest?.ai_review_status === "running") && (
                <span className="text-xs text-sky-300 animate-pulse">AI проверяет…</span>
              )}
              {!latest && <span className="text-xs text-slate-600">ещё нет сдачи</span>}
            </div>
          </button>

          <div className="w-px bg-white/10" />

          <div className="shrink-0 flex items-center gap-1 px-2">
            <button
              type="button"
              onClick={toggleMusic}
              className={`px-2.5 py-1.5 rounded-md text-xs font-semibold ${
                musicOn ? "bg-teal-600 text-white" : "text-slate-400 hover:bg-white/10"
              }`}
            >
              {musicOn ? "❚❚" : "▶"}
            </button>
            <button
              type="button"
              onClick={() => setLofiOpen((v) => !v)}
              className="px-2 py-1.5 rounded-md text-[11px] text-slate-400 hover:bg-white/10"
            >
              Lo-fi {lofiOpen ? "▾" : "▸"}
            </button>
          </div>
        </div>

        {resultOpen && (
          <div className="px-4 pb-3 max-h-40 overflow-y-auto border-t border-white/5">
            {!latest && (
              <p className="text-xs text-slate-500 pt-2">Сдай файл справа — здесь появится проверка.</p>
            )}
            {latest?.tutor_comment && (
              <div className="mt-2 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-200">
                <p className="text-[10px] uppercase text-slate-500 font-semibold mb-1">Репетитор</p>
                {latest.tutor_comment}
              </div>
            )}
            {(latest?.ai_review_status === "pending" || latest?.ai_review_status === "running") && (
              <div className="mt-2 rounded-md border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-xs text-sky-100">
                AI проверяет решение… обычно 10–30 сек
              </div>
            )}
            {latest?.ai_review_status === "done" && latest.ai_verdict && (
              <div className={`mt-2 rounded-md border px-3 py-2 text-xs ${resultTone(latest.ai_verdict)}`}>
                <p className="font-bold">
                  {AI_VERDICT_LABEL[latest.ai_verdict] || latest.ai_verdict}
                  {latest.ai_verdict !== "unclear" && latest.ai_score != null
                    ? ` · ${latest.ai_score}%`
                    : ""}
                </p>
                {latest.ai_feedback && (
                  <p className="mt-1.5 leading-relaxed opacity-90">{latest.ai_feedback}</p>
                )}
              </div>
            )}
            {latest?.ai_review_status === "error" && (
              <p className="mt-2 text-xs text-rose-300">
                {latest.ai_review_error || "Ошибка AI-проверки"}
              </p>
            )}
          </div>
        )}

        {lofiOpen && (
          <div className="px-4 pb-3 border-t border-white/5 space-y-2">
            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={toggleMusic}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold ${
                  musicOn ? "bg-teal-600 text-white" : "bg-white/10 text-slate-200"
                }`}
              >
                {musicOn ? "Пауза" : "Играть"}
              </button>
              <label className="flex items-center gap-2 text-xs text-slate-400 flex-1">
                <span className="shrink-0">Громк.</span>
                <input
                  type="range"
                  min={0.05}
                  max={0.4}
                  step={0.01}
                  value={volume}
                  onChange={(e) => setVolume(Number(e.target.value))}
                  className="flex-1 accent-teal-400"
                />
              </label>
            </div>
          </div>
        )}
      </footer>
    </div>
  );
}
