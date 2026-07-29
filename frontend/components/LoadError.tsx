"use client";

import Alert from "@/components/Alert";

export default function LoadError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="max-w-lg mx-auto mt-16 space-y-4">
      <Alert message={message} />
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rc-btn-primary w-full sm:w-auto"
        >
          Повторить
        </button>
      )}
    </div>
  );
}
