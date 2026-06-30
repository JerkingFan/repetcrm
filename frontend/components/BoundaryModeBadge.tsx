import {
  BOUNDARY_MODE_SHORT,
  BOUNDARY_MODE_STYLES,
  parseBoundaryMode,
} from "@/lib/boundaries";

export default function BoundaryModeBadge({ mode }: { mode?: string | null }) {
  const parsed = parseBoundaryMode(mode);
  if (parsed === "normal") return null;

  const styles = BOUNDARY_MODE_STYLES[parsed];
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles.badge}`}
      title="Режим границ ученика"
    >
      <span className={`w-1.5 h-1.5 rounded-full ${styles.dot}`} />
      {BOUNDARY_MODE_SHORT[parsed]}
    </span>
  );
}
