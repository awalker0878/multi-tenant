import { defineConfig, devices } from '@playwright/test';
const browser = process.env.P03_BROWSER_ENGINE ?? 'chromium';
if (browser !== 'chromium' && browser !== 'firefox' && browser !== 'webkit') throw new Error('Unsupported P03 browser engine');
const profiles = { chromium: 'Desktop Chrome', firefox: 'Desktop Firefox', webkit: 'Desktop Safari' };
export default defineConfig({
  testDir: '.', forbidOnly: true, retries: 0, workers: 1, timeout: 150_000, globalTimeout: 180_000,
  reporter: [['list'], ['json', { outputFile: 'test-results/p03-browser.json' }]],
  use: { baseURL: process.env.CONSOLE_BASE_URL, ignoreHTTPSErrors: true, trace: 'off', screenshot: 'off', video: 'off' },
  projects: [{ name: browser, use: { ...devices[profiles[browser]], browserName: browser } }],
});
