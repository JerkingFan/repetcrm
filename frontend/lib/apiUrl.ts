/** Локальная разработка: фронт :3000, API :8000 */
function isLocalDevHost(hostname: string, port: string): boolean {
  return (
    (hostname === "localhost" || hostname === "127.0.0.1") &&
    (port === "3000" || port === "3001")
  );
}

function isStandardWebPort(port: string): boolean {
  return port === "" || port === "80" || port === "443";
}

function isDirectFrontendPort(port: string): boolean {
  return port === "3000" || port === "3001";
}

/**
 * Подгоняет NEXT_PUBLIC_API_URL под текущую страницу.
 * Порт 8000 — только HTTP (uvicorn без SSL). HTTPS-страница → /api через nginx.
 */
function normalizeApiBaseForPage(raw: string, page: Location): string {
  const trimmed = raw.trim().replace(/\/$/, "");
  if (!trimmed) return "/api";
  if (trimmed.startsWith("/")) return trimmed;

  let api: URL;
  try {
    api = new URL(trimmed);
  } catch {
    return "/api";
  }

  const sameHost = api.hostname === page.hostname;
  const pageHttps = page.protocol === "https:";

  // :8000 никогда не отдаёт HTTPS — иначе ERR_SSL_PROTOCOL_ERROR
  if (api.port === "8000") {
    if (pageHttps) return "/api";
    return `http://${api.hostname}:8000`;
  }

  // Сайт по HTTPS: API только через тот же домен /api (не IP:8000 и не http→https апгрейд)
  if (pageHttps) {
    if (!sameHost || api.protocol === "http:") return "/api";
    if (!api.pathname.startsWith("/api")) {
      api.pathname = api.pathname === "/" ? "/api" : `/api${api.pathname}`;
    }
    return api.toString().replace(/\/$/, "");
  }

  // HTTP: фронт на :3000 → бэкенд на :8000
  if (isDirectFrontendPort(page.port) && sameHost) {
    return `http://${page.hostname}:8000`;
  }

  // HTTP через nginx (порт 80)
  if (sameHost && isStandardWebPort(page.port)) {
    if (!api.port && (api.pathname === "" || api.pathname === "/")) return "/api";
    if (!api.port && !api.pathname.startsWith("/api")) {
      api.pathname = `/api${api.pathname}`.replace(/\/api\/api/, "/api");
      return `${api.origin}${api.pathname}`.replace(/\/$/, "");
    }
  }

  if (!sameHost && isStandardWebPort(page.port)) {
    return "/api";
  }

  if (api.protocol === "https:" && page.protocol === "http:") {
    api.protocol = "http:";
    return api.toString().replace(/\/$/, "");
  }

  return api.toString().replace(/\/$/, "");
}

/**
 * Базовый URL API для fetch и ссылок на PDF/LaTeX.
 */
export function getApiUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();

  if (typeof window !== "undefined") {
    const { hostname, port, protocol } = window.location;

    if (isLocalDevHost(hostname, port)) {
      return `http://${hostname}:8000`;
    }

    if (protocol === "https:") {
      if (fromEnv) return normalizeApiBaseForPage(fromEnv, window.location);
      return "/api";
    }

    if (isDirectFrontendPort(port)) {
      if (fromEnv) return normalizeApiBaseForPage(fromEnv, window.location);
      return `http://${hostname}:8000`;
    }

    if (fromEnv) return normalizeApiBaseForPage(fromEnv, window.location);
    return "/api";
  }

  if (fromEnv) return fromEnv.replace(/\/$/, "");
  return "http://localhost:8000";
}
