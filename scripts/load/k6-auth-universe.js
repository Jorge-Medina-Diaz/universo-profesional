/**
 * k6 load test: 200 concurrent users doing login + fetch universe.
 *
 * Run:
 *   k6 run --env BASE_URL=http://localhost:8000 scripts/load/k6-auth-universe.js
 *
 * Requires a pre-seeded user (register + verify once before the test):
 *   export K6_EMAIL=load@example.com
 *   export K6_PASSWORD=SecurePass123!
 */
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const EMAIL = __ENV.K6_EMAIL || "load@example.com";
const PASSWORD = __ENV.K6_PASSWORD || "SecurePass123!";

export const options = {
  stages: [
    { duration: "30s", target: 50 },
    { duration: "1m", target: 200 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<1000"],
    http_req_failed: ["rate<0.05"],
  },
};

export default function () {
  // Login
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(loginRes, {
    "login status is 200": (r) => r.status === 200,
    "login has access_token": (r) => r.json("access_token") !== "",
  });

  const token = loginRes.json("access_token");

  // Fetch universe
  const universeRes = http.get(`${BASE_URL}/api/v1/universe/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  check(universeRes, {
    "universe status is 200": (r) => r.status === 200,
  });

  sleep(1);
}
