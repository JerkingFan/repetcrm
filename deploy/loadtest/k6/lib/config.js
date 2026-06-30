export function baseUrl() {
  return (__ENV.BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

export function usersFile() {
  return __ENV.USERS_FILE || "/data/users.json";
}

export function jsonHeaders(token) {
  const h = { "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export function monthRange() {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const fmt = (d) => d.toISOString().slice(0, 10);
  return { from: fmt(from), to: fmt(to) };
}
