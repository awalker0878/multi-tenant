import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser-p02',
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 60_000,
  globalTimeout: 150_000,
  reporter: [['list'], ['json', { outputFile: 'test-results/p02-browser.json' }]],
  // The browser trusts only a disposable self-signed fixture here; Governance verifies its CA.
  // These tests handle ephemeral deployment credentials; no request/body traces.
  use: { baseURL: process.env.CONSOLE_BASE_URL, ignoreHTTPSErrors: true, trace: 'off', screenshot: 'off', video: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
