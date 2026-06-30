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

export default function () {
  const url = baseUrl();

  const health = http.get(`${url}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  const user = firstUser();
  const login = http.post(
    `${url}/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers: jsonHeaders(), tags: { name: "login" } }
  );
  check(login, {
    "login 200": (r) => r.status === 200,
    "login has token": (r) => r.json("access_token"),
  });

  const token = login.json("access_token");
  const dash = http.get(`${url}/dashboard`, {
    headers: jsonHeaders(token),
    tags: { name: "dashboard" },
  });
  check(dash, { "dashboard 200": (r) => r.status === 200 });

  sleep(0.5);
}
