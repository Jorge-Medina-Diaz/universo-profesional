/**
 * k6 load test: 50 concurrent users generating CV with mock LLM.
 *
 * Run:
 *   k6 run --env BASE_URL=http://localhost:8000 scripts/load/k6-generate-cv.js
 *
 * Requires a pre-seeded user with some universe data.
 */
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const EMAIL = __ENV.K6_EMAIL || "load@example.com";
const PASSWORD = __ENV.K6_PASSWORD || "SecurePass123!";

export const options = {
  stages: [
    { duration: "20s", target: 10 },
    { duration: "1m", target: 50 },
    { duration: "20s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<5000"],
    http_req_failed: ["rate<0.1"],
  },
};

export default function () {
  // Login
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(loginRes, { "login ok": (r) => r.status === 200 });

  const token = loginRes.json("access_token");

  // Generate CV
  const cvRes = http.post(
    `${BASE_URL}/api/v1/documents/generate-cv`,
    JSON.stringify({
      job_description: "Senior backend engineer with Python and FastAPI",
      template: "ats-classic",
      language: "es",
    }),
    { headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } }
  );
  check(cvRes, {
    "cv generate status is 201": (r) => r.status === 201,
    "cv has document_id": (r) => r.json("document_id") !== "",
  });

  sleep(2);
}
