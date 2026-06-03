"use client";

import { useEffect, useRef } from "react";
import type { BoardState } from "@/components/Whiteboard";

type Bounds = { minX: number; minY: number; maxX: number; maxY: number };

function normalizeState(raw: BoardState | undefined): BoardState {
  const s = (raw || {}) as Partial<BoardState>;
  return {
    version: 1,
    strokes: Array.isArray(s.strokes) ? s.strokes : [],
    texts: Array.isArray(s.texts) ? s.texts : [],
    images: Array.isArray(s.images) ? s.images : [],
  };
}

function computeBounds(state: BoardState): Bounds | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  const add = (x: number, y: number) => {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  };

  for (const st of state.strokes) {
    for (const pt of st.points || []) add(pt.x, pt.y);
  }
  for (const t of state.texts) {
    const w = Math.max((t.text || "").length, 1) * (t.size || 24) * 0.55;
    const h = (t.size || 24) * 1.25;
    add(t.x, t.y);
    add(t.x + w, t.y + h);
  }
  for (const im of state.images) {
    add(im.x, im.y);
    add(im.x + im.w, im.y + im.h);
  }

  if (!Number.isFinite(minX)) return null;
  return { minX, minY, maxX, maxY };
}

function resolveImageUrl(url: string): string {
  if (typeof window === "undefined") return url;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/")) return `${window.location.origin}${url}`;
  return url;
}

export default function BoardPreview({
  state: rawState,
  className = "",
}: {
  state?: BoardState;
  className?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let cancelled = false;
    const state = normalizeState(rawState);

    const draw = async () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(1, Math.floor(rect.width * dpr));
      const h = Math.max(1, Math.floor(rect.height * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, w, h);

      const bounds = computeBounds(state);
      if (!bounds) {
        ctx.strokeStyle = "rgba(15, 23, 42, 0.08)";
        ctx.lineWidth = 1;
        const step = w / 8;
        for (let x = 0; x <= w; x += step) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, h);
          ctx.stroke();
        }
        for (let y = 0; y <= h; y += step) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }
        ctx.fillStyle = "#94a3b8";
        ctx.font = `${Math.round(11 * dpr)}px Inter, system-ui, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("Пустая доска", w / 2, h / 2);
        return;
      }

      const pad = Math.max((bounds.maxX - bounds.minX) * 0.08, 0.02);
      const bw = bounds.maxX - bounds.minX + pad * 2;
      const bh = bounds.maxY - bounds.minY + pad * 2;
      const scale = Math.min(w / bw, h / bh);
      const ox = (w - bw * scale) / 2 - (bounds.minX - pad) * scale;
      const oy = (h - bh * scale) / 2 - (bounds.minY - pad) * scale;

      ctx.save();
      ctx.translate(ox, oy);
      ctx.scale(scale, scale);

      for (const st of state.strokes) {
        const pts = st.points || [];
        if (pts.length < 1) continue;
        ctx.strokeStyle = st.color || "#1E3A8A";
        ctx.lineWidth = Math.max((st.width || 3) / scale, 0.5 / dpr);
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        ctx.stroke();
      }

      for (const t of state.texts) {
        if (!t.text) continue;
        ctx.fillStyle = t.color || "#1E3A8A";
        const fontSize = Math.max((t.size || 24) / scale, 4 / dpr);
        ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
        ctx.textBaseline = "top";
        ctx.fillText(t.text, t.x, t.y);
      }

      for (const im of state.images) {
        if (!im.url) continue;
        try {
          const image = new Image();
          image.crossOrigin = "anonymous";
          await new Promise<void>((resolve, reject) => {
            image.onload = () => resolve();
            image.onerror = () => reject(new Error("load failed"));
            image.src = resolveImageUrl(im.url);
          });
          if (cancelled) return;
          ctx.drawImage(image, im.x, im.y, im.w, im.h);
        } catch {
          ctx.fillStyle = "rgba(148, 163, 184, 0.35)";
          ctx.fillRect(im.x, im.y, im.w, im.h);
        }
      }

      ctx.restore();
    };

    draw();
    return () => {
      cancelled = true;
    };
  }, [rawState]);

  return (
    <canvas
      ref={canvasRef}
      className={`block w-full h-full ${className}`}
      aria-hidden
    />
  );
}
