/**
 * Stress test: ramp until errors or high latency (find breaking point).
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { baseUrl, jsonHeaders, monthRange } from "./lib/config.js";
import { firstUser } from "./lib/users.js";

export const options = {
  scenarios: {
    stress: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: 25 },
        { duration: "1m", target: 50 },
        { duration: "1m", target: 75 },
        { duration: "1m", target: 100 },
        { duration: "1m", target: 0 },
      ],
      gracefulRampDown: "20s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1500"],
  },
};

export function setup() {
  const user = firstUser();
  const url = baseUrl();
  const login = http.post(
    `${url}/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers: jsonHeaders() }
  );
  if (login.status !== 200) throw new Error(`stress setup login failed: ${login.body}`);
  return { token: login.json("access_token") };
}

export default function (data) {
  const url = baseUrl();
  const headers = jsonHeaders(data.token);
  const range = monthRange();

  const endpoints = [
    () => http.get(`${url}/dashboard`, { headers, tags: { name: "dashboard" } }),
    () => http.get(`${url}/students?page=1`, { headers, tags: { name: "students" } }),
    () =>
      http.get(`${url}/lessons?from=${range.from}&to=${range.to}`, {
        headers,
        tags: { name: "lessons" },
      }),
  ];

  const pick = endpoints[Math.floor(Math.random() * endpoints.length)];
  const res = pick();
  check(res, { ok: (r) => r.status === 200 });
  sleep(0.3);
}
