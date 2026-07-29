import { test, expect } from "@playwright/test";

// The landing hero reads "Tu carrera ahora tiene memoria. Y agente propio."
// with the primary CTA "Crear mi memoria" and a top-nav "Iniciar sesión".
// The redesign renamed the CTA from "Crear mi universo"; because these specs
// had never run in CI, the stale label went unnoticed. Both controls are
// <button>s that navigate by pushing a hash — neither is a link.
// Multiple controls share these labels (hero + final CTA + nav), so every
// locator is scoped with .first() to avoid Playwright strict-mode violations.
test.describe("Landing page", () => {
  test("renders hero headline and CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1").first()).toContainText("memoria");
    await expect(
      page.getByRole("button", { name: /Crear mi memoria/i }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Iniciar sesión/i }).first(),
    ).toBeVisible();
  });

  test("primary CTA navigates to register", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Crear mi memoria/i }).first().click();
    await expect(page).toHaveURL(/#\/register/);
  });

  test("login control navigates to login", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Iniciar sesión/i }).first().click();
    await expect(page).toHaveURL(/#\/login/);
  });
});
