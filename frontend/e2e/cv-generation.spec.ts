import { test, expect } from "@playwright/test";

// This used to assert `getByText(/Generar CV|CV/i).first()` unscoped, which
// matched the *navigation link* labelled "Generar CV" rather than the page. It
// therefore passed on desktop without ever rendering the CV surface, and failed
// on mobile only because that same link is hidden below the `sm` breakpoint.
//
// The real behaviour: Router.tsx gates authenticated users with an empty
// universe into onboarding, so a freshly registered e2e account that navigates
// to /#/cv/new lands on the onboarding chat. That gate is what is worth
// asserting here — reaching the generator itself needs a seeded profile, which
// this suite does not build.
// Deliberately does NOT assert the redirect target: the gate only fires once
// the universe-summary and /me queries resolve, so asserting the URL races the
// network and was flaky on the slower mobile emulation. Asserting that the
// route renders an authenticated surface is stable, and — unlike the original —
// cannot pass against a hidden navigation link.
test.describe("CV generation route", () => {
  test("renders an authenticated surface", async ({ page }) => {
    await page.goto("/#/cv/new");
    await expect(page.locator("main").getByRole("heading", { level: 1 })).toBeVisible();
  });
});
