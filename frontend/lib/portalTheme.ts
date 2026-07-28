/** Student portal visual customization presets */

export const PORTAL_THEMES = [
  {
    id: "ocean",
    swatch: "linear-gradient(135deg,#1d4ed8,#0ea5e9)",
  },
  {
    id: "forest",
    swatch: "linear-gradient(135deg,#166534,#22c55e)",
  },
  {
    id: "sunset",
    swatch: "linear-gradient(135deg,#c2410c,#f59e0b)",
  },
  {
    id: "midnight",
    swatch: "linear-gradient(135deg,#1e1b4b,#6366f1)",
  },
  {
    id: "candy",
    swatch: "linear-gradient(135deg,#db2777,#f472b6)",
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
    ocean: "Океан",
    forest: "Лес",
    sunset: "Закат",
    midnight: "Ночь",
    candy: "Конфетка",
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
        "--portal-bg": "radial-gradient(ellipse at top, #dcfce7 0%, #f0fdf4 45%, #ecfdf5 100%)",
        "--portal-accent": "#166534",
        "--portal-accent-soft": "rgba(22,101,52,0.7)",
        "--portal-hero": "linear-gradient(135deg,#166534,#22c55e)",
      };
    case "sunset":
      return {
        "--portal-bg": "radial-gradient(ellipse at top, #ffedd5 0%, #fff7ed 45%, #fef3c7 100%)",
        "--portal-accent": "#c2410c",
        "--portal-accent-soft": "rgba(194,65,12,0.7)",
        "--portal-hero": "linear-gradient(135deg,#c2410c,#f59e0b)",
      };
    case "midnight":
      return {
        "--portal-bg": "radial-gradient(ellipse at top, #e0e7ff 0%, #eef2ff 45%, #f5f3ff 100%)",
        "--portal-accent": "#4338ca",
        "--portal-accent-soft": "rgba(67,56,202,0.7)",
        "--portal-hero": "linear-gradient(135deg,#312e81,#6366f1)",
      };
    case "candy":
      return {
        "--portal-bg": "radial-gradient(ellipse at top, #fce7f3 0%, #fdf2f8 45%, #fae8ff 100%)",
        "--portal-accent": "#be185d",
        "--portal-accent-soft": "rgba(190,24,93,0.7)",
        "--portal-hero": "linear-gradient(135deg,#db2777,#f472b6)",
      };
    default:
      return {
        "--portal-bg": "radial-gradient(ellipse at top, #e8eefc 0%, #f8fafc 45%, #f1f5f9 100%)",
        "--portal-accent": "#1e40af",
        "--portal-accent-soft": "rgba(30,64,175,0.7)",
        "--portal-hero": "linear-gradient(135deg,#1e40af,#2563eb)",
      };
  }
}
