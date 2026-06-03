"use client";

export default function Alert({
  type = "error",
  message,
  onClose,
}: {
  type?: "error" | "success" | "info";
  message: string;
  onClose?: () => void;
}) {
  const styles = {
    error: "bg-red-50 text-red-800 border-red-200",
    success: "bg-emerald-50 text-emerald-800 border-emerald-200",
    info: "bg-blue-50 text-blue-800 border-blue-200",
  };
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm flex justify-between gap-4 ${styles[type]}`}>
      <span>{message}</span>
      {onClose && (
        <button onClick={onClose} className="shrink-0 font-medium hover:opacity-70">
          ×
        </button>
      )}
    </div>
  );
}
