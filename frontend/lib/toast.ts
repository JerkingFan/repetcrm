export type ToastType = "error" | "success" | "info";

type ToastHandler = (message: string, type?: ToastType) => void;

let handler: ToastHandler | null = null;

export function registerToast(fn: ToastHandler) {
  handler = fn;
}

export function unregisterToast() {
  handler = null;
}

/** Неблокирующее уведомление (требует ToastProvider в дереве). */
export function toast(message: string, type: ToastType = "info") {
  if (handler) {
    handler(message, type);
    return;
  }
  if (typeof window !== "undefined") {
    console.warn("[toast]", type, message);
  }
}
