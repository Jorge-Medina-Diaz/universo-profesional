import { test, expect } from "@playwright/test";

test.describe("Mobile viewport", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test.beforeEach(async ({ page }) => {
    await page.goto("/#/universe");
  });

  test("bottom navigation is visible", async ({ page }) => {
    const nav = page.locator("nav[aria-label='Navegación principal']");
    await expect(nav).toBeVisible();
    await expect(nav.getByText("Chat")).toBeVisible();
    await expect(nav.getByText("Universo")).toBeVisible();
    await expect(nav.getByText("Conectar")).toBeVisible();
    await expect(nav.getByText("Ajustes")).toBeVisible();
  });

  test("bottom nav links navigate", async ({ page }) => {
    const nav = page.locator("nav[aria-label='Navegación principal']");
    await nav.getByText("Universo").click();
    await expect(page).toHaveURL(/\/#\/universe/);
    await nav.getByText("Conectar").click();
    await expect(page).toHaveURL(/\/#\/connections/);
    await nav.getByText("Ajustes").click();
    await expect(page).toHaveURL(/\/#\/settings/);
  });
});
