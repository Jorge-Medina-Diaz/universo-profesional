import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration.
 * - Desktop + mobile projects
 * - webServer auto-starts `npm run dev` before tests
 * - Global setup creates a single test user and seeds auth state
 * - Screenshots and traces on first retry
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-setup.ts",
  use: {
    baseURL: "http://localhost:5173",
    locale: "es-ES",
    storageState: "./e2e/.auth/user.json",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "Mobile Chrome", use: { ...devices["Pixel 5"] } },
  ],
  webServer: {
    command:
      process.platform === "win32"
        ? "set VITE_BACKEND_URL=http://localhost:8000 && npm run dev"
        : "VITE_BACKEND_URL=http://localhost:8000 npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
