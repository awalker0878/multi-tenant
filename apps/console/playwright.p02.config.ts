import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser-p02',
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 30_000,
  globalTimeout: 90_000,
  reporter: [['list'], ['json', { outputFile: 'test-results/p02-browser.json' }]],
  // These tests handle ephemeral deployment credentials; no request/body traces.
  use: { baseURL: process.env.CONSOLE_BASE_URL, trace: 'off', screenshot: 'off', video: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
