import { expect, test } from '@playwright/test';

test('the compiled Console page hydrates and discloses its foundation state', async ({ page, browser }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await testInfo.attach('browser-identity', {
    body: JSON.stringify({ engine: browser.browserType().name(), version: browser.version() }),
    contentType: 'application/json',
  });
  const response = await page.goto('/');
  expect(response?.status()).toBe(200);
  await expect(page).toHaveTitle('Workload Mobility | Foundation');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Enterprise Workload Mobility and Secure Hosting');
  await expect(page.getByRole('heading', { name: 'Console foundation' })).toBeVisible();
  await expect(page.getByText('Development stage: foundation')).toBeVisible();
  await expect(page.getByRole('button')).toHaveCount(0);
  expect(await page.locator('body').evaluate(element => element.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
