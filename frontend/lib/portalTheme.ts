/** Student portal visual customization presets */

export const PORTAL_THEMES = [
  {
    id: "ocean",
    swatch: "linear-gradient(135deg,#0e7490 0%,#155e75 45%,#042f2e 100%)",
  },
  {
    id: "forest",
    swatch: "linear-gradient(135deg,#15803d 0%,#166534 50%,#052e16 100%)",
  },
  {
    id: "sunset",
    swatch: "linear-gradient(135deg,#ea580c 0%,#c2410c 45%,#7c2d12 100%)",
  },
  {
    id: "midnight",
    swatch: "linear-gradient(135deg,#1e293b 0%,#0f172a 50%,#020617 100%)",
  },
  {
    id: "candy",
    swatch: "linear-gradient(135deg,#e11d48 0%,#be123c 45%,#881337 100%)",
  },
] as const;

export const PORTAL_AVATARS = [
  { id: "rocket", emoji: "🚀" },
  { id: "fox", emoji: "🦊" },
  { id: "cat", emoji: "🐱" },
  { id: "owl", emoji: "🦉" },
  { id: "dragon", emoji: "🐉" },
  { id: "star", emoji: "⭐" },
  { id: "book", emoji: "📚" },
  { id: "bolt", emoji: "⚡" },
] as const;

export function themeLabel(id: string): string {
  const map: Record<string, string> = {
    ocean: "Глубина",
    forest: "Хвоя",
    sunset: "Зарево",
    midnight: "Графит",
    candy: "Сигнал",
  };
  return map[id] || id;
}

export function avatarLabel(id: string): string {
  return PORTAL_AVATARS.find((a) => a.id === id)?.emoji || "🚀";
}

export function avatarEmoji(id?: string): string {
  return PORTAL_AVATARS.find((a) => a.id === id)?.emoji || "🚀";
}

/** CSS variables for portal shell background / accents */
export function themeVars(theme?: string): Record<string, string> {
  switch (theme) {
    case "forest":
      return {
        "--portal-bg":
          "radial-gradient(ellipse 120% 80% at 10% -10%, #bbf7d0 0%, transparent 55%), radial-gradient(ellipse 90% 70% at 100% 0%, #86efac55 0%, transparent 50%), linear-gradient(180deg, #f0fdf4 0%, #ecfdf5 40%, #f8fafc 100%)",
        "--portal-accent": "#14532d",
        "--portal-accent-soft": "rgba(20,83,45,0.65)",
        "--portal-hero": "linear-gradient(145deg, #052e16 0%, #166534 42%, #22c55e 100%)",
        "--portal-signal": "#22c55e",
        "--portal-ink": "#052e16",
        "--portal-orb-a": "rgba(34,197,94,0.35)",
        "--portal-orb-b": "rgba(21,128,61,0.22)",
        "--portal-card": "rgba(255,255,255,0.72)",
        "--portal-card-border": "rgba(21,128,61,0.12)",
      };
    case "sunset":
      return {
        "--portal-bg":
          "radial-gradient(ellipse 120% 80% at 0% -5%, #fed7aa 0%, transparent 55%), radial-gradient(ellipse 80% 60% at 100% 10%, #fdba7455 0%, transparent 50%), linear-gradient(180deg, #fff7ed 0%, #ffedd5 35%, #f8fafc 100%)",
        "--portal-accent": "#9a3412",
        "--portal-accent-soft": "rgba(154,52,18,0.7)",
        "--portal-hero": "linear-gradient(145deg, #7c2d12 0%, #c2410c 48%, #fb923c 100%)",
        "--portal-signal": "#f97316",
        "--portal-ink": "#431407",
        "--portal-orb-a": "rgba(249,115,22,0.35)",
        "--portal-orb-b": "rgba(234,88,12,0.2)",
        "--portal-card": "rgba(255,255,255,0.74)",
        "--portal-card-border": "rgba(194,65,12,0.12)",
      };
    case "midnight":
      return {
        "--portal-bg":
          "radial-gradient(ellipse 110% 70% at 15% -10%, #94a3b8aa 0%, transparent 50%), radial-gradient(ellipse 80% 50% at 100% 0%, #64748b44 0%, transparent 45%), linear-gradient(180deg, #e2e8f0 0%, #f1f5f9 45%, #f8fafc 100%)",
        "--portal-accent": "#0f172a",
        "--portal-accent-soft": "rgba(15,23,42,0.65)",
        "--portal-hero": "linear-gradient(145deg, #020617 0%, #1e293b 50%, #334155 100%)",
        "--portal-signal": "#38bdf8",
        "--portal-ink": "#020617",
        "--portal-orb-a": "rgba(56,189,248,0.28)",
        "--portal-orb-b": "rgba(148,163,184,0.25)",
        "--portal-card": "rgba(255,255,255,0.78)",
        "--portal-card-border": "rgba(15,23,42,0.1)",
      };
    case "candy":
      return {
        "--portal-bg":
          "radial-gradient(ellipse 120% 80% at 5% -10%, #fecdd3 0%, transparent 55%), radial-gradient(ellipse 90% 60% at 100% 5%, #fda4af55 0%, transparent 50%), linear-gradient(180deg, #fff1f2 0%, #ffe4e6 40%, #f8fafc 100%)",
        "--portal-accent": "#9f1239",
        "--portal-accent-soft": "rgba(159,18,57,0.7)",
        "--portal-hero": "linear-gradient(145deg, #881337 0%, #e11d48 48%, #fb7185 100%)",
        "--portal-signal": "#fb7185",
        "--portal-ink": "#4c0519",
        "--portal-orb-a": "rgba(244,63,94,0.32)",
        "--portal-orb-b": "rgba(251,113,133,0.22)",
        "--portal-card": "rgba(255,255,255,0.74)",
        "--portal-card-border": "rgba(225,29,72,0.12)",
      };
    default:
      return {
        "--portal-bg":
          "radial-gradient(ellipse 120% 80% at 8% -8%, #99f6e4 0%, transparent 52%), radial-gradient(ellipse 90% 70% at 100% 0%, #67e8f955 0%, transparent 48%), linear-gradient(180deg, #ecfeff 0%, #f0fdfa 38%, #f8fafc 100%)",
        "--portal-accent": "#115e59",
        "--portal-accent-soft": "rgba(17,94,89,0.7)",
        "--portal-hero": "linear-gradient(145deg, #042f2e 0%, #0f766e 46%, #2dd4bf 100%)",
        "--portal-signal": "#2dd4bf",
        "--portal-ink": "#042f2e",
        "--portal-orb-a": "rgba(45,212,191,0.38)",
        "--portal-orb-b": "rgba(14,116,144,0.22)",
        "--portal-card": "rgba(255,255,255,0.7)",
        "--portal-card-border": "rgba(15,118,110,0.14)",
      };
  }
}
