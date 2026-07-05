type CacheEntry = {
  img: HTMLImageElement;
  status: "loading" | "ready" | "error";
};

export function resolveBoardImageUrl(url: string, shareToken?: string): string {
  if (typeof window === "undefined") return url;
  let resolved = url;
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    if (url.startsWith("/")) {
      resolved = `${window.location.origin}${url}`;
    }
  }
  if (!shareToken || resolved.includes("token=")) return resolved;
  if (!resolved.includes("/media/boards/")) return resolved;
  const sep = resolved.includes("?") ? "&" : "?";
  return `${resolved}${sep}token=${encodeURIComponent(shareToken)}`;
}

/** Возвращает закэшированное изображение или начинает загрузку; onReady вызывается один раз при успехе. */
export function getBoardImage(
  cache: Map<string, CacheEntry>,
  url: string,
  onReady?: () => void,
  shareToken?: string
): HTMLImageElement | null {
  const key = resolveBoardImageUrl(url, shareToken);
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
