import { test, expect } from "@playwright/test";

test.describe("Landing page", () => {
  test("renders hero headline and CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Sustituye el CV en Word por un universo vivo");
    await expect(page.getByRole("button", { name: /Empezar gratis/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Ya tengo cuenta/i })).toBeVisible();
  });

  test("navigates to register", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Empezar gratis/i }).click();
    await expect(page).toHaveURL(/\/#\/register/);
  });

  test("navigates to login", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Ya tengo cuenta/i }).click();
    await expect(page).toHaveURL(/\/#\/login/);
  });
});
