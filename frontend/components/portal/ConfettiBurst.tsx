"use client";

import { useEffect, useState } from "react";

/** Lightweight confetti burst (no deps). */
export default function ConfettiBurst({ active, durationMs = 2200 }: { active: boolean; durationMs?: number }) {
  const [pieces, setPieces] = useState<
    Array<{ id: number; left: number; delay: number; color: string; rot: number }>
  >([]);

  useEffect(() => {
    if (!active) {
      setPieces([]);
      return;
    }
    const colors = ["#22c55e", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6"];
    setPieces(
      Array.from({ length: 28 }, (_, i) => ({
        id: i,
        left: 8 + Math.random() * 84,
        delay: Math.random() * 0.35,
        color: colors[i % colors.length],
        rot: Math.random() * 360,
      }))
    );
    const t = setTimeout(() => setPieces([]), durationMs);
    return () => clearTimeout(t);
  }, [active, durationMs]);

  if (!pieces.length) return null;

  return (
    <div className="pointer-events-none fixed inset-0 z-[60] overflow-hidden" aria-hidden>
      {pieces.map((p) => (
        <span
          key={p.id}
          className="absolute top-0 w-2 h-3 rounded-sm confetti-piece"
          style={{
            left: `${p.left}%`,
            background: p.color,
            animationDelay: `${p.delay}s`,
            transform: `rotate(${p.rot}deg)`,
          }}
        />
      ))}
    </div>
  );
}
