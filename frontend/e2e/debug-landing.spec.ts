import { test, expect } from "@playwright/test";

test("debug landing page on prod build with source maps", async ({ page }) => {
  page.on("console", (msg) => {
    console.log(`[${msg.type()}] ${msg.text()}`);
  });
  page.on("pageerror", (err) => {
    console.log(`[PAGE ERROR] ${err.message}`);
    console.log(err.stack);
  });
  page.on("response", (resp) => {
    if (resp.status() >= 400) {
      console.log(`[HTTP ${resp.status()}] ${resp.url()}`);
    }
  });

  await page.goto("http://localhost:8080/");
  await page.waitForTimeout(3000);

  const errorText = await page.locator("text=Algo ha petado en la UI").isVisible().catch(() => false);
  console.log("Error boundary visible:", errorText);

  expect(true).toBe(true);
});
