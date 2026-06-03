"use client";

import { useEffect, useRef } from "react";
import type { BoardState } from "@/components/Whiteboard";

type Bounds = { minX: number; minY: number; maxX: number; maxY: number };
type Point = { x: number; y: number };

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

/** Толщина штриха на доске в мировых координатах (как в Whiteboard). */
function strokeWidthWorld(strokeWidth: number, canvasPixels = 1200): number {
  return (strokeWidth || 3) / canvasPixels;
}

/** Толщина линии в пикселях превью. */
function strokeWidthPreviewPx(strokeWidth: number, fitScale: number): number {
  const world = strokeWidthWorld(strokeWidth);
  return Math.max(0.75, Math.min(2.5, world * fitScale));
}

function resolveImageUrl(url: string): string {
  if (typeof window === "undefined") return url;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/")) return `${window.location.origin}${url}`;
  return url;
}

function drawStrokePath(ctx: CanvasRenderingContext2D, pts: Point[], toScreen: (p: Point) => Point) {
  if (pts.length < 1) return;
  const p0 = toScreen(pts[0]);
  ctx.beginPath();
  ctx.moveTo(p0.x, p0.y);
  if (pts.length === 2) {
    const p1 = toScreen(pts[1]);
    ctx.lineTo(p1.x, p1.y);
  } else if (pts.length > 2) {
    for (let i = 1; i < pts.length - 1; i++) {
      const pt = toScreen(pts[i]);
      const next = toScreen(pts[i + 1]);
      const midX = (pt.x + next.x) / 2;
      const midY = (pt.y + next.y) / 2;
      ctx.quadraticCurveTo(pt.x, pt.y, midX, midY);
    }
    const last = toScreen(pts[pts.length - 1]);
    ctx.lineTo(last.x, last.y);
  }
  ctx.stroke();
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
      const fitScale = Math.min(w / bw, h / bh);
      const ox = (w - bw * fitScale) / 2;
      const oy = (h - bh * fitScale) / 2;

      const toScreen = (p: Point): Point => ({
        x: (p.x - bounds.minX + pad) * fitScale + ox,
        y: (p.y - bounds.minY + pad) * fitScale + oy,
      });

      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      for (const st of state.strokes) {
        const pts = st.points || [];
        if (pts.length < 1) continue;
        ctx.strokeStyle = st.color || "#1E3A8A";
        ctx.lineWidth = strokeWidthPreviewPx(st.width, fitScale);
        drawStrokePath(ctx, pts, toScreen);
      }

      for (const t of state.texts) {
        if (!t.text) continue;
        const topLeft = toScreen({ x: t.x, y: t.y });
        const worldFont = (t.size || 24) / 1200;
        const fontPx = Math.max(8, Math.min(14, worldFont * fitScale));
        ctx.fillStyle = t.color || "#1E3A8A";
        ctx.font = `${fontPx}px Inter, system-ui, sans-serif`;
        ctx.textBaseline = "top";
        ctx.fillText(t.text, topLeft.x, topLeft.y);
      }

      for (const im of state.images) {
        if (!im.url) continue;
        const tl = toScreen({ x: im.x, y: im.y });
        const br = toScreen({ x: im.x + im.w, y: im.y + im.h });
        const iw = br.x - tl.x;
        const ih = br.y - tl.y;
        if (iw < 1 || ih < 1) continue;
        try {
          const image = new Image();
          image.crossOrigin = "anonymous";
          await new Promise<void>((resolve, reject) => {
            image.onload = () => resolve();
            image.onerror = () => reject(new Error("load failed"));
            image.src = resolveImageUrl(im.url);
          });
          if (cancelled) return;
          ctx.drawImage(image, tl.x, tl.y, iw, ih);
        } catch {
          ctx.fillStyle = "rgba(148, 163, 184, 0.35)";
          ctx.fillRect(tl.x, tl.y, iw, ih);
        }
      }
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
