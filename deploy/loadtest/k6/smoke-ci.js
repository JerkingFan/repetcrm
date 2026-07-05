import http from "k6/http";
import { check, sleep } from "k6";

/** Self-contained smoke for CI — no users.json required. Uses HttpOnly cookies. */

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<3000"],
  },
};

const base = (__ENV.BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const email = __ENV.SMOKE_EMAIL || "smoke-ci@test.example";
const password = __ENV.SMOKE_PASSWORD || "smokepass1234";
const jar = http.cookieJar();

function jsonHeaders() {
  return { "Content-Type": "application/json" };
}

export function setup() {
  const reg = http.post(
    `${base}/auth/register`,
    JSON.stringify({ email, password, name: "CI Smoke" }),
    { headers: jsonHeaders() }
  );
  if (reg.status !== 200 && reg.status !== 400 && reg.status !== 422) {
    throw new Error(`register failed: ${reg.status} ${reg.body}`);
  }
}

export default function () {
  const health = http.get(`${base}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  const login = http.post(
    `${base}/auth/login`,
    JSON.stringify({ email, password }),
    { headers: jsonHeaders(), jar }
  );
  check(login, { "login 200": (r) => r.status === 200 });

  const me = http.get(`${base}/auth/me`, { jar });
  check(me, {
    "me 200": (r) => r.status === 200,
    "me email": (r) => r.json("email") === email,
  });

  const dash = http.get(`${base}/dashboard`, { jar });
  check(dash, { "dashboard 200": (r) => r.status === 200 });

  sleep(0.2);
}
