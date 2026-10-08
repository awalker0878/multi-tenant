import { defineConfig, devices } from '@playwright/test';

const browser = process.env.P02_BROWSER_ENGINE ?? 'chromium';
if (browser !== 'chromium' && browser !== 'firefox' && browser !== 'webkit') {
  throw new Error('Unsupported P02 browser engine.');
}
const profiles = { chromium: 'Desktop Chrome', firefox: 'Desktop Firefox', webkit: 'Desktop Safari' };

export default defineConfig({
  testDir: './tests/browser-p02',
  forbidOnly: true,
  retries: 0,
  workers: 1,
  // Includes real 15-second notification polling through two application processes.
  timeout: 90_000,
  globalTimeout: 180_000,
  reporter: [['list'], ['json', { outputFile: 'test-results/p02-browser.json' }]],
  // The browser trusts only a disposable self-signed fixture here; Governance verifies its CA.
  // These tests handle ephemeral deployment credentials; no request/body traces.
  use: { baseURL: process.env.CONSOLE_BASE_URL, ignoreHTTPSErrors: true, trace: 'off', screenshot: 'off', video: 'off' },
  projects: [{ name: browser, use: { ...devices[profiles[browser]], browserName: browser } }],
});
