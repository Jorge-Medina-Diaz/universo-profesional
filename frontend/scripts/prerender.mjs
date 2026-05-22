/**
 * Post-build pre-render: walks `dist/index.html` through a headless browser,
 * captures the landing page HTML, and writes it back so Googlebot sees the
 * full content without executing JS.
 *
 * Why not just trust JS-rendering Googlebot? Because:
 *   - Bing, DuckDuckGo, and most LinkedIn/WhatsApp/Slack scrapers DON'T
 *     execute JS. They take whatever's in the initial HTML.
 *   - First Contentful Paint drops from ~1.5s to ~150ms — huge UX win.
 *
 * The script is best-effort: if puppeteer is unavailable (no CI cache,
 * Alpine without chrome) we skip and the build still succeeds. The hosted
 * Fly.io / Railway image with this enabled gets the benefit; local dev
 * doesn't pay the cost.
 *
 * To enable in CI/CD:
 *   npm i -D puppeteer-core @puppeteer/browsers
 *   PRERENDER=true npm run build
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const distDir = join(__dirname, "..", "dist");
const indexPath = join(distDir, "index.html");

if (process.env.PRERENDER !== "true") {
  console.log("[prerender] skipping (set PRERENDER=true to enable)");
  process.exit(0);
}

if (!existsSync(indexPath)) {
  console.error("[prerender] dist/index.html not found — run `vite build` first");
  process.exit(1);
}

let puppeteer;
try {
  puppeteer = (await import("puppeteer")).default;
} catch {
  try {
    puppeteer = (await import("puppeteer-core")).default;
  } catch {
    console.log("[prerender] puppeteer not installed — skipping");
    process.exit(0);
  }
}

const port = 4173;
const { createServer } = await import("node:http");
const { createReadStream } = await import("node:fs");
const { lookup } = await import("node:dns").then((m) => m.promises ? m : { promises: m });

// Tiny static server pointing at dist/
const mime = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".webmanifest": "application/manifest+json",
  ".json": "application/json",
  ".xml": "text/xml",
  ".txt": "text/plain",
};
const server = createServer((req, res) => {
  let path = (req.url || "/").split("?")[0];
  if (path === "/") path = "/index.html";
  const file = join(distDir, path);
  if (!existsSync(file)) {
    res.writeHead(200, { "Content-Type": "text/html" });
    createReadStream(indexPath).pipe(res);
    return;
  }
  const ext = path.slice(path.lastIndexOf("."));
  res.writeHead(200, { "Content-Type": mime[ext] || "application/octet-stream" });
  createReadStream(file).pipe(res);
});
await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));

try {
  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  const page = await browser.newPage();
  await page.setUserAgent("PrerenderBot/1.0 (compatible; +https://universo.pro)");
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle0", timeout: 30000 });
  // Strip auth-only nav remnants by waiting for the landing's hero to settle.
  await page.waitForSelector("[data-landing-ready], main, #root > div", { timeout: 8000 }).catch(() => {});
  // Mark as pre-rendered so the SPA knows to hydrate carefully.
  await page.evaluate(() => {
    document.documentElement.setAttribute("data-prerendered", "true");
    window.__PRERENDERED__ = true;
  });
  const html = await page.content();
  writeFileSync(indexPath, html, "utf8");
  console.log("[prerender] wrote dist/index.html (%d bytes)", html.length);
  await browser.close();
} catch (err) {
  console.error("[prerender] failed:", err.message);
  process.exitCode = 0; // never break the build
} finally {
  server.close();
}
