"use client";

import { useEffect, useRef, useState } from "react";
import { formatRuDate, homeworkDueLabel } from "@/lib/portalUi";
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

/** Soft study lo-fi: vinyl crackle + warm pad + light beat via Web Audio. */
class LofiEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private nodes: AudioNode[] = [];
  private timers: number[] = [];
  private playing = false;

  async start() {
    if (this.playing) return;
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
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
      // soft crackle, mostly quiet with occasional pops
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
    // mellow jazz-ish progression in A minor-ish: Am7 · Dm7 · G7 · Cmaj7 (freq mid)
    const chords = [
      [220.0, 261.63, 329.63, 392.0], // A C E G
      [146.83, 174.61, 220.0, 349.23], // D F A C
      [196.0, 246.94, 293.66, 349.23], // G B D F
      [130.81, 164.81, 196.0, 261.63], // C E G C
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
        osc.frequency.value = f * 0.5; // octave down, warmer
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
    const stepMs = (60_000 / bpm) / 2; // eighths
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
  const engineRef = useRef<LofiEngine | null>(null);
  const [musicOn, setMusicOn] = useState(false);
  const [volume, setVolume] = useState(0.22);

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
      engineRef.current?.stop();
      engineRef.current = null;
    }
  }, [open]);

  useEffect(() => {
    return () => {
      engineRef.current?.stop();
      engineRef.current = null;
    };
  }, []);

  useEffect(() => {
    engineRef.current?.setVolume(volume);
  }, [volume]);

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

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-[#0a0e17] text-slate-100 overflow-y-auto">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,_#1a3a4a_0%,_transparent_50%),radial-gradient(ellipse_at_80%_100%,_#2a1f4a33_0%,_transparent_45%)]" />

      <div className="relative max-w-lg mx-auto px-4 pt-5 pb-20 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-teal-300/80 font-semibold">
              Режим фокуса
            </p>
            <h2 className="text-xl font-bold mt-0.5 tracking-tight">Твои задания</h2>
          </div>
          <button
            type="button"
            onClick={() => {
              engineRef.current?.stop();
              engineRef.current = null;
              onClose();
            }}
            className="px-3 py-2 rounded-xl border border-white/15 text-sm text-slate-300 hover:bg-white/5 shrink-0"
          >
            Выйти
          </button>
        </div>

        {/* Tasks first — always visible */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <h3 className="font-semibold text-slate-100">
              {todos.length > 0 ? `Сделать · ${todos.length}` : "Задания"}
            </h3>
            {todos.length > 0 && (
              <span className="text-[11px] text-slate-500">нажми — открыть</span>
            )}
          </div>
          {todos.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">
              Всё сдано. Можно открыть доску или просто посидеть с lo-fi.
            </p>
          ) : (
            <ul className="space-y-2.5">
              {todos.map((h, i) => {
                const due = homeworkDueLabel(h.due_date);
                return (
                  <li key={h.id} className="portal-focus-item" style={{ animationDelay: `${i * 45}ms` }}>
                    <button
                      type="button"
                      onClick={() => {
                        engineRef.current?.stop();
                        engineRef.current = null;
                        onClose();
                        onOpenHomework(h.id);
                      }}
                      className="w-full text-left rounded-xl border border-white/12 bg-black/25 px-3.5 py-3.5 hover:border-teal-400/50 hover:bg-black/35 transition"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-50">
                          {formatRuDate(h.lesson_date)}
                        </p>
                        {h.submission_status === "needs_revision" && (
                          <span className="text-[10px] font-bold uppercase tracking-wide text-amber-300 shrink-0">
                            доработать
                          </span>
                        )}
                      </div>
                      {h.preview && (
                        <p className="text-sm text-slate-300 mt-1.5 leading-snug line-clamp-3">
                          {h.preview}
                        </p>
                      )}
                      <div className="mt-2.5 flex items-center justify-between gap-2">
                        {due ? (
                          <span
                            className={`text-[11px] font-medium ${
                              due.urgent ? "text-rose-300" : "text-slate-500"
                            }`}
                          >
                            {due.text}
                          </span>
                        ) : (
                          <span />
                        )}
                        <span className="text-[12px] font-semibold text-teal-300">Решать →</span>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* Lo-fi + board controls */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={toggleMusic}
              className={`px-4 py-2.5 rounded-xl text-sm font-semibold transition ${
                musicOn
                  ? "bg-teal-500 text-white shadow-lg shadow-teal-900/40"
                  : "bg-white/10 text-slate-200 border border-white/10"
              }`}
            >
              {musicOn ? "Lo-fi ●" : "Lo-fi ▶"}
            </button>
            {boardLesson?.board_url && (
              <a
                href={boardLesson.board_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2.5 rounded-xl bg-white/10 border border-white/10 text-sm font-semibold"
              >
                Доска
              </a>
            )}
            {boardLesson?.meeting_url && (
              <a
                href={boardLesson.meeting_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2.5 rounded-xl bg-emerald-500/90 text-white text-sm font-semibold"
              >
                В урок
              </a>
            )}
          </div>

          {musicOn && (
            <label className="flex items-center gap-3 text-xs text-slate-400">
              <span className="shrink-0 w-10">Громк.</span>
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
          )}

          <p className="text-[11px] text-slate-500 leading-relaxed">
            {musicOn
              ? "Тихий бит · винил · тёплые аккорды — прямо в браузере, без сторонних треков."
              : "Включи lo-fi, если хочешь фон. Задания уже сверху — можно сразу решать."}
          </p>
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
