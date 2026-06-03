type CacheEntry = {
  img: HTMLImageElement;
  status: "loading" | "ready" | "error";
};

export function resolveBoardImageUrl(url: string): string {
  if (typeof window === "undefined") return url;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/")) return `${window.location.origin}${url}`;
  return url;
}

/** Возвращает закэшированное изображение или начинает загрузку; onReady вызывается один раз при успехе. */
export function getBoardImage(
  cache: Map<string, CacheEntry>,
  url: string,
  onReady?: () => void
): HTMLImageElement | null {
  const key = resolveBoardImageUrl(url);
  let entry = cache.get(key);

  if (!entry) {
    const img = new Image();
    img.crossOrigin = "anonymous";
    entry = { img, status: "loading" };
    cache.set(key, entry);
    img.onload = () => {
      entry!.status = "ready";
      onReady?.();
    };
    img.onerror = () => {
      entry!.status = "error";
    };
    img.src = key;
  }

  return entry.status === "ready" ? entry.img : null;
}

export function pruneImageCache(cache: Map<string, CacheEntry>, usedUrls: Set<string>) {
  for (const key of [...cache.keys()]) {
    if (!usedUrls.has(key)) cache.delete(key);
  }
}
