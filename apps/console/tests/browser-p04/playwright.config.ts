import { defineConfig, devices } from '@playwright/test';
const browser = process.env.P04_BROWSER_ENGINE ?? 'chromium';
if (browser !== 'chromium' && browser !== 'firefox' && browser !== 'webkit') throw new Error('Unsupported P04 browser engine');
const profiles = { chromium: 'Desktop Chrome', firefox: 'Desktop Firefox', webkit: 'Desktop Safari' };
export default defineConfig({
  testDir: '.', forbidOnly: true, retries: 0, workers: 1, timeout: 150_000, globalTimeout: 180_000,
  outputDir: '../../test-results/p04-artifacts',
  reporter: [['list'], ['json', { outputFile: '../../test-results/p04-browser.json' }]],
  use: { baseURL: process.env.CONSOLE_BASE_URL, actionTimeout: 15_000, navigationTimeout: 15_000, trace: 'off', screenshot: 'off', video: 'off' },
  projects: [{ name: browser, use: { ...devices[profiles[browser]], browserName: browser } }],
});
