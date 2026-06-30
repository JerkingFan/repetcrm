export type BoundaryMode = "normal" | "yellow" | "orange" | "red";

export const BOUNDARY_MODE_LABELS: Record<BoundaryMode, string> = {
  normal: "Обычный режим",
  yellow: "Жёлтый — переносы",
  orange: "Оранжевый — предоплата",
  red: "Красный — жёсткие границы",
};

export const BOUNDARY_MODE_SHORT: Record<BoundaryMode, string> = {
  normal: "Норма",
  yellow: "Жёлтый",
  orange: "Оранжевый",
  red: "Красный",
};

export const BOUNDARY_MODE_STYLES: Record<
  BoundaryMode,
  { badge: string; panel: string; dot: string }
> = {
  normal: {
    badge: "bg-slate-100 text-slate-700 border-slate-200",
    panel: "bg-slate-50 border-slate-200",
    dot: "bg-slate-400",
  },
  yellow: {
    badge: "bg-amber-50 text-amber-900 border-amber-200",
    panel: "bg-amber-50 border-amber-200",
    dot: "bg-amber-500",
  },
  orange: {
    badge: "bg-orange-50 text-orange-900 border-orange-200",
    panel: "bg-orange-50 border-orange-200",
    dot: "bg-orange-500",
  },
  red: {
    badge: "bg-red-50 text-red-900 border-red-200",
    panel: "bg-red-50 border-red-200",
    dot: "bg-red-500",
  },
};

export const BOUNDARY_SIGNAL_LABELS: Record<string, string> = {
  reschedules_30d: "Переносы за 30 дней",
  no_show_60d: "Неявки за 60 дней",
  late_30d: "Опоздания за 30 дней",
  unpaid_past: "Неоплаченные уроки",
};

export function parseBoundaryMode(raw: string | undefined | null): BoundaryMode {
  if (raw === "yellow" || raw === "orange" || raw === "red") return raw;
  return "normal";
}

export const MODE_SEVERITY: Record<BoundaryMode, number> = {
  normal: 0,
  yellow: 1,
  orange: 2,
  red: 3,
};
