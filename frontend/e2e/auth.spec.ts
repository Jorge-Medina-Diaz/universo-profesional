import { test, expect } from "@playwright/test";

const TEST_EMAIL = `e2e-${Date.now()}@example.com`;
const TEST_PASSWORD = "TestPassword123!";

async function dismissCookies(page: import("@playwright/test").Page) {
  const btn = page.getByRole("button", { name: "Solo necesarias" });
  if (await btn.isVisible().catch(() => false)) {
    await btn.click();
  }
}

test.describe.serial("Auth flow", () => {
  // Auth tests start from a clean browser state (no pre-seeded session).
  test.use({ storageState: undefined });

  test("register a new account", async ({ page }) => {
    await page.goto("/#/register");
    await dismissCookies(page);
    await page.getByPlaceholder("Tu nombre").fill("E2E Test");
    await page.getByLabel(/Email/i).fill(TEST_EMAIL);
    await page.getByLabel(/Contraseña/i).fill(TEST_PASSWORD);
    await page.locator("form").getByRole("button", { name: /Registrarme/i }).click();

    // If verification is required in dev, click the bypass button.
    const verifyNow = page.locator("[role='main']").getByRole("button", { name: "Verificar ahora (dev)" });
    if (await verifyNow.isVisible().catch(() => false)) {
      await verifyNow.click();
    }

    // Should eventually land on onboarding or home.
    await expect(page).toHaveURL(/\/#\/(onboarding)?/);
  });

  test("login with the created account", async ({ page }) => {
    await page.goto("/#/login");
    await dismissCookies(page);
    await page.getByLabel(/Email/i).fill(TEST_EMAIL);
    await page.getByLabel(/Contraseña/i).fill(TEST_PASSWORD);
    await page.locator("form").getByRole("button", { name: /Entrar/i }).click();
    await expect(page).toHaveURL(/\/#\//);
  });

  test("shows error on invalid credentials", async ({ page }) => {
    await page.goto("/#/login");
    await dismissCookies(page);
    await page.getByLabel(/Email/i).fill("no-existe@example.com");
    await page.getByLabel(/Contraseña/i).fill("wrong");
    await page.locator("form").getByRole("button", { name: /Entrar/i }).click();
    await expect(page.getByText(/incorrecto|inválido|error/i)).toBeVisible();
  });
});

test.describe("Auth cleanup", () => {
  test.afterAll(async ({ request }) => {
    const loginRes = await request.post("/api/v1/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    if (!loginRes.ok()) return;
    const body = await loginRes.json();
    const token = body.access_token;
    await request.delete("/api/v1/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
  });
});
