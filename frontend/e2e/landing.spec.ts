import { test, expect } from "@playwright/test";

// The landing hero reads "Tu carrera ahora tiene memoria. Y agente propio."
// with the primary CTA "Crear mi memoria" and a top-nav "Iniciar sesión".
// The redesign renamed the CTA from "Crear mi universo"; because these specs
// had never run in CI, the stale label went unnoticed. Both controls are
// <button>s that navigate by pushing a hash — neither is a link.
// Multiple controls share these labels (hero + final CTA + nav), so every
// locator is scoped with .first() to avoid Playwright strict-mode violations.
test.describe("Landing page", () => {
  // The public landing only renders when signed OUT — "/" serves the
  // authenticated home (h1 "Tu carrera, viva") when a session exists, and the
  // config seeds one for every spec. These tests only ever passed because
  // global-setup was silently failing to authenticate.
  test.use({ storageState: { cookies: [], origins: [] } });

  test("renders hero headline and primary CTA", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1").first()).toContainText("memoria");
    await expect(
      page.getByRole("button", { name: /Crear mi memoria/i }).first(),
    ).toBeVisible();
  });

  // The nav "Iniciar sesión" control is `hidden sm:block`, so below the 640px
  // breakpoint it does not exist for the user — the mobile landing collapses it
  // into the hamburger menu. Asserting it on a 393px Pixel 5 tests markup the
  // design deliberately hides.
  test("nav shows a login control on desktop", async ({ page, isMobile }) => {
    test.skip(!!isMobile, "nav login is desktop-only; mobile uses the hamburger");
    await page.goto("/");
    await expect(
      page.getByRole("button", { name: /Iniciar sesión/i }).first(),
    ).toBeVisible();
  });

  test("primary CTA navigates to register", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Crear mi memoria/i }).first().click();
    await expect(page).toHaveURL(/#\/register/);
  });

  test("login control navigates to login", async ({ page, isMobile }) => {
    test.skip(!!isMobile, "nav login is desktop-only; mobile uses the hamburger");
    await page.goto("/");
    await page.getByRole("button", { name: /Iniciar sesión/i }).first().click();
    await expect(page).toHaveURL(/#\/login/);
  });
});
