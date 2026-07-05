import http from "k6/http";
import { check, sleep } from "k6";
import { baseUrl, jsonHeaders } from "./lib/config.js";
import { firstUser } from "./lib/users.js";

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const jar = http.cookieJar();

export default function () {
  const url = baseUrl();

  const health = http.get(`${url}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  const user = firstUser();
  const login = http.post(
    `${url}/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers: jsonHeaders(), jar, tags: { name: "login" } }
  );
  check(login, { "login 200": (r) => r.status === 200 });

  const me = http.get(`${url}/auth/me`, { jar, tags: { name: "me" } });
  check(me, { "me 200": (r) => r.status === 200 });

  const dash = http.get(`${url}/dashboard`, {
    jar,
    tags: { name: "dashboard" },
  });
  check(dash, { "dashboard 200": (r) => r.status === 200 });

  sleep(0.5);
}
