/** Сессия в HttpOnly cookies (access + refresh). localStorage не используется. */

export function hasLegacyToken(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(window.localStorage.getItem("repetcrm_token"));
}

/** Удалить устаревший токен из localStorage после миграции на cookies. */
export function clearLegacyToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("repetcrm_token");
}
