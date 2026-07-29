export type QueuedMutation = {
  id: string;
  method: string;
  path: string;
  body?: string;
  createdAt: number;
};

const QUEUE_KEY = "repetcrm_offline_queue_v1";
const CACHE_INDEX_KEY = "repetcrm_offline_cache_index_v1";

function safeJsonParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function loadQueue(): QueuedMutation[] {
  return safeJsonParse<QueuedMutation[]>(localStorage.getItem(QUEUE_KEY)) || [];
}

export function saveQueue(queue: QueuedMutation[]) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export function enqueueMutation(input: Omit<QueuedMutation, "id" | "createdAt">) {
  const queue = loadQueue();
  const next: QueuedMutation = {
    ...input,
    id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
    createdAt: Date.now(),
  };
  queue.push(next);
  saveQueue(queue);
  return next.id;
}

export async function flushQueue(send: (m: QueuedMutation) => Promise<boolean>) {
  const queue = loadQueue();
  if (!queue.length) return;

  const nextQueue: QueuedMutation[] = [];
  for (let i = 0; i < queue.length; i++) {
    const item = queue[i];
    try {
      const ok = await send(item);
      if (!ok) {
        nextQueue.push(...queue.slice(i));
        break;
      }
    } catch {
      nextQueue.push(...queue.slice(i));
      break;
    }
  }
  saveQueue(nextQueue);
}

export function getOfflineCache(cacheKey: string) {
  return safeJsonParse<unknown>(localStorage.getItem(cacheKey));
}

export function setOfflineCache(cacheKey: string, payload: unknown) {
  const json = JSON.stringify(payload);
  localStorage.setItem(cacheKey, json);

  // Keep a small bounded index to avoid unbounded localStorage growth.
  const maxEntries = 40;
  const index = safeJsonParse<string[]>(localStorage.getItem(CACHE_INDEX_KEY)) || [];
  const nextIndex = Array.from(new Set([cacheKey, ...index])).slice(0, maxEntries);

  localStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(nextIndex));
  // Note: old keys beyond nextIndex are left as-is (simple, safe).
}

