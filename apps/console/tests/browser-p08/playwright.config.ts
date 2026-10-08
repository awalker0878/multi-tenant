import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: '*.spec.ts', forbidOnly: true, retries: 0, workers: 1,
  timeout: 60_000, globalTimeout: 120_000,
  outputDir: '../../test-results/p08-artifacts',
  reporter: [['list'], ['json', { outputFile: '../../test-results/p08-browser.json' }]],
  use: { baseURL: 'http://127.0.0.1:4188', ...devices['Desktop Chrome'], launchOptions: process.env.P08_CHROMIUM_EXECUTABLE ? { executablePath: process.env.P08_CHROMIUM_EXECUTABLE, args: ['--no-sandbox', '--disable-gpu'] } : {}, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: { command: 'npx vite --config tests/browser-p08/vite.config.ts', cwd: new URL('../..', import.meta.url).pathname, url: 'http://127.0.0.1:4188/__fixture', reuseExistingServer: false },
});
