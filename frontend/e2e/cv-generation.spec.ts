import { test, expect } from "@playwright/test";

test.describe("CV generation page", () => {
  test("loads the generate CV surface", async ({ page }) => {
    await page.goto("/#/cv/new");
    await expect(page.getByText(/Generar CV|CV/i).first()).toBeVisible();
  });
});
