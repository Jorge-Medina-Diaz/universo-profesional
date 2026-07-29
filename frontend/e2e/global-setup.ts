import { request } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.join(__dirname, ".auth");
const AUTH_FILE = path.join(AUTH_DIR, "user.json");

export const TEST_EMAIL = `e2e-global@${Date.now()}.example.com`;
export const TEST_PASSWORD = "TestPassword123!";

export default async function globalSetup() {
  const ctx = await request.newContext({ baseURL: "http://localhost:5173" });

  // Register global test user.
  await ctx.post("/api/v1/auth/register", {
    data: {
      email: TEST_EMAIL,
      password: TEST_PASSWORD,
      display_name: "E2E Global",
      locale: "es-ES",
    },
  });

  // Login to obtain tokens.
  const loginRes = await ctx.post("/api/v1/auth/login", {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });
  const body = await loginRes.json();

  // Fail loudly. This used to write a storage state with an undefined token
  // whenever login failed (401 "Email not verified" when
  // AUTO_VERIFY_EMAILS_IN_DEV is off), so every authenticated spec silently
  // redirected to /login and failed with an unrelated-looking locator timeout.
  if (!loginRes.ok() || !body.access_token) {
    throw new Error(
      `global-setup: login failed (HTTP ${loginRes.status()}): ${JSON.stringify(body)}. ` +
        `The backend must accept the freshly registered account. Common causes: ` +
        `401 "Email not verified" (set AUTO_VERIFY_EMAILS_IN_DEV=true), or ` +
        `429 (auth is rate-limited to 10 requests / 15 min — set RATE_LIMIT_ENABLED=false).`,
    );
  }

  // Build Playwright storage state for localStorage.
  const storageState = {
    origins: [
      {
        origin: "http://localhost:5173",
        localStorage: [
          {
            name: "cvs-saas-auth",
            value: JSON.stringify({
              accessToken: body.access_token,
              refreshToken: body.refresh_token,
              userId: body.user_id,
              email: body.email,
            }),
          },
          {
            name: "cvs-saas-cookie-consent",
            value: JSON.stringify({
              necessary: true,
              analytics: false,
              marketing: false,
              decided_at: new Date().toISOString(),
            }),
          },
        ],
      },
    ],
  };

  fs.mkdirSync(AUTH_DIR, { recursive: true });
  fs.writeFileSync(AUTH_FILE, JSON.stringify(storageState, null, 2));

  await ctx.dispose();
}

export async function globalTeardown() {
  const ctx = await request.newContext({ baseURL: "http://localhost:5173" });
  const loginRes = await ctx.post("/api/v1/auth/login", {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });
  if (loginRes.ok()) {
    const body = await loginRes.json();
    await ctx.delete("/api/v1/users/me", {
      headers: { Authorization: `Bearer ${body.access_token}` },
    });
  }
  await ctx.dispose();
  try {
    fs.unlinkSync(AUTH_FILE);
  } catch {
    /* ignore */
  }
}
