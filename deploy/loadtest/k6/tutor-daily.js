/**
 * Simulates a typical tutor session: dashboard → students → lessons → student detail.
 * 50 VUs ≈ 50 concurrent tutors (target production load).
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import { baseUrl, jsonHeaders, monthRange, usersFile } from "./lib/config.js";

const usersPayload = new SharedArray("users", function () {
  return [JSON.parse(open(usersFile()))];
});

export const options = {
  scenarios: {
    tutor_daily: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: __ENV.RAMP_UP || "30s", target: Number(__ENV.VUS || 50) },
        { duration: __ENV.STEADY || "2m", target: Number(__ENV.VUS || 50) },
        { duration: __ENV.RAMP_DOWN || "20s", target: 0 },
      ],
      gracefulRampDown: "15s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    http_req_duration: ["p(95)<800", "p(99)<2000"],
    "http_req_duration{name:dashboard}": ["p(95)<500"],
    "http_req_duration{name:students_list}": ["p(95)<600"],
    "http_req_duration{name:lessons_list}": ["p(95)<700"],
    checks: ["rate>0.95"],
  },
};

export function setup() {
  const url = baseUrl();
  const health = http.get(`${url}/health`);
  if (health.status !== 200) {
    throw new Error(`Backend unhealthy: ${health.status} ${health.body}`);
  }

  const users = usersPayload[0].users;
  const tokens = [];

  for (let i = 0; i < users.length; i++) {
    const u = users[i];
    const res = http.post(
      `${url}/auth/login`,
      JSON.stringify({ email: u.email, password: u.password }),
      { headers: jsonHeaders(), tags: { name: "setup_login" } }
    );
    if (res.status !== 200) {
      console.warn(`setup login failed for ${u.email}: ${res.status} ${res.body}`);
      continue;
    }
    tokens.push({ email: u.email, token: res.json("access_token") });
    sleep(0.05);
  }

  if (tokens.length === 0) {
    throw new Error("No tokens obtained in setup — run seed script first");
  }

  console.log(`setup: ${tokens.length}/${users.length} tutors logged in`);
  return { tokens };
}

export default function (data) {
  const url = baseUrl();
  const session = data.tokens[(__VU - 1) % data.tokens.length];
  const headers = jsonHeaders(session.token);
  const range = monthRange();

  const dash = http.get(`${url}/dashboard`, { headers, tags: { name: "dashboard" } });
  check(dash, { dashboard_ok: (r) => r.status === 200 });

  const students = http.get(`${url}/students?page=1&page_size=20`, {
    headers,
    tags: { name: "students_list" },
  });
  check(students, {
    students_ok: (r) => r.status === 200,
    students_has_items: (r) => Array.isArray(r.json("items")),
  });

  const lessons = http.get(`${url}/lessons?from=${range.from}&to=${range.to}`, {
    headers,
    tags: { name: "lessons_list" },
  });
  check(lessons, {
    lessons_ok: (r) => r.status === 200,
    lessons_is_array: (r) => Array.isArray(r.json()),
  });

  const me = http.get(`${url}/auth/me`, { headers, tags: { name: "me" } });
  check(me, { me_ok: (r) => r.status === 200 });

  const items = students.json("items") || [];
  if (items.length > 0) {
    const sid = items[0].id;
    const detail = http.get(`${url}/students/${sid}`, {
      headers,
      tags: { name: "student_detail" },
    });
    check(detail, { student_detail_ok: (r) => r.status === 200 });
  }

  sleep(Number(__ENV.THINK_TIME || 1));
}
