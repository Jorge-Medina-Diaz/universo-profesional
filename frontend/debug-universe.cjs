// eslint-disable-next-line @typescript-eslint/no-require-imports
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ locale: 'es-ES', viewport: { width: 1280, height: 720 } });
  const page = await context.newPage();

  const logs = [];
  page.on('console', msg => logs.push({ type: msg.type(), text: msg.text() }));
  page.on('pageerror', err => logs.push({ type: 'pageerror', text: err.message }));

  await page.goto('http://localhost:5173/');
  await page.waitForTimeout(3000);

  // Check if we're on login or already authed
  const url = page.url();
  console.log('Initial URL:', url);

  // Try to auth via API to bypass UI
  const reg = await page.request.post('http://localhost:5173/api/v1/auth/register', {
    data: { email: 'debug-universe@example.com', password: 'TestPassword123!', display_name: 'Debug', locale: 'es-ES' }
  });
  console.log('Register status:', reg.status());

  const login = await page.request.post('http://localhost:5173/api/v1/auth/login', {
    data: { email: 'debug-universe@example.com', password: 'TestPassword123!' }
  });
  const body = await login.json().catch(() => ({}));
  console.log('Login status:', login.status());

  if (body.access_token) {
    await page.evaluate((tokens) => {
      globalThis.localStorage.setItem('cvs-saas-auth', JSON.stringify(tokens));
      globalThis.localStorage.setItem('cvs-saas-cookie-consent', JSON.stringify({ necessary: true, analytics: false, marketing: false, decided_at: new Date().toISOString() }));
    }, { accessToken: body.access_token, refreshToken: body.refresh_token, userId: body.user_id, email: body.email });
    await page.reload();
    await page.waitForTimeout(3000);
  }

  console.log('Post-auth URL:', page.url());

  // Navigate to universe
  await page.goto('http://localhost:5173/#/universe');
  await page.waitForTimeout(5000);

  console.log('Universe URL:', page.url());
  await page.screenshot({ path: '/tmp/debug-universe.png', fullPage: true });
  console.log('Screenshot saved');

  console.log('\n--- Console logs ---');
  logs.forEach(l => console.log(`[${l.type}] ${l.text}`));

  await browser.close();
})();
