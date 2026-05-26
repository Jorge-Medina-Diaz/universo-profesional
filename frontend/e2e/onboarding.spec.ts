import { test, expect } from "@playwright/test";

test.describe("Onboarding wizard", () => {
  test("renders welcome step and advances", async ({ page }) => {
    await page.goto("/#/onboarding");
    await expect(page.getByText("Bienvenido", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: /Empezar/i }).click();
    await expect(page).toHaveURL(/step=import/);
  });

  test("persists step across reloads", async ({ page }) => {
    await page.goto("/#/onboarding");
    await page.getByRole("button", { name: /Empezar/i }).click();
    await expect(page.getByText("Importar datos")).toBeVisible();

    await page.reload();
    await expect(page.getByText("Importar datos")).toBeVisible();
  });

  test("back button works", async ({ page }) => {
    await page.goto("/#/onboarding?step=import");
    await expect(page.getByText("Importar datos")).toBeVisible();
    await page.getByRole("button", { name: /Atrás/i }).click();
    await expect(page.getByText("Bienvenido", { exact: false })).toBeVisible();
  });
});
