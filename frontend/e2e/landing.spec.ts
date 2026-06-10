import { test, expect } from "@playwright/test";

// The landing hero reads "Tu carrera no es un CV. Es un universo." with the
// primary CTA "Crear mi universo" and a top-nav "Iniciar sesión".
// Multiple controls share these labels (hero + final CTA + nav), so every
// locator is scoped with .first() to avoid Playwright strict-mode violations.
test.describe("Landing page", () => {
  test("renders hero headline and CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1").first()).toContainText("memoria");
    await expect(
      page.getByRole("button", { name: /Crear mi universo/i }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Iniciar sesión/i }).first(),
    ).toBeVisible();
  });

  test("primary CTA navigates to register", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /Crear mi universo/i }).first().click();
    await expect(page).toHaveURL(/#\/register/);
  });

  test("login control navigates to login", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Iniciar sesión/i }).first().click();
    await expect(page).toHaveURL(/#\/login/);
  });
});
