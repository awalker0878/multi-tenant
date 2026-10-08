import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';

test('browses scoped observations, preserves uncertain enrollment and clears revoked access', async ({ browser, request }) => {
  const fixture = JSON.parse(readFileSync(process.env.P04_BROWSER_FIXTURE!, 'utf8'));
  const context = await browser.newContext({ baseURL: process.env.CONSOLE_BASE_URL });
  await context.addCookies([fixture.admin_cookie]);
  const page = await context.newPage();
  const errors: string[] = [];
  page.on('pageerror', error => { errors.push(error.message); console.error(error.message); });
  const base = `/tenants/${fixture.tenant}/inventory/sites/${fixture.site}`;
  await page.goto(base);
  await expect(page.getByRole('heading', { name: 'Site inventory', exact: true })).toBeVisible();
  await page.getByText('Installed declarations and capability gaps', { exact: true }).click();
  await expect(page.getByText(/UNASSESSED/)).toHaveCount(11);
  await page.getByRole('link', { name: 'Browse observations' }).click();
  await expect(page.getByRole('heading', { name: 'Observed resources', exact: true })).toBeVisible();
  await expect(page.getByRole('row')).toHaveCount(5);
  await expect(page.locator('img')).toHaveCount(0);
  await page.getByLabel('Filter this page').fill('vm-1');
  await expect(page.getByRole('row')).toHaveCount(2);
  await expect(page.getByRole('rowheader')).toContainText('<img src=x onerror=alert(1)>');
  await page.getByRole('button', { name: 'Propose application match', exact: true }).click();
  await expect(page.getByLabel('Application ID', { exact: true })).toBeFocused();
  await expect(page.getByText('These resources remain observation-only.', { exact: false })).toBeVisible();
  await page.setViewportSize({ width: 640, height: 800 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth+2)).toBe(true);
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true);
  await page.evaluate(() => { document.documentElement.style.zoom = '1'; });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole('link', { name: 'Site health and discovery' }).click();
  await page.getByLabel('Approved scope').selectOption(fixture.second_policy);
  await page.getByLabel('Endpoint label').fill('Browser enrolled scope');
  writeFileSync(fixture.fault_file, JSON.stringify({ path: `/v1/tenants/${fixture.tenant}/sites/${fixture.site}/endpoints` }));
  await page.getByRole('button', { name: 'Enroll for read-only discovery', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('uncertain');
  await expect(page.getByRole('alert')).toBeFocused();
  await expect(page.getByLabel('Endpoint label')).toHaveValue('Browser enrolled scope');
  await expect(page.getByLabel('Endpoint label')).toBeDisabled();
  await page.getByRole('button', { name: 'Retry unchanged command', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Command accepted');
  await expect(page.getByRole('heading', { name: 'Browser enrolled scope', exact: true })).toHaveCount(1);

  await page.getByRole('link', { name: 'Environment configuration', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Environment configuration and porting review' })).toBeVisible();
  await expect(page.getByText('2026.2 Hibiscus', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Compute flavors required', { exact: true })).toBeChecked();
  await expect(page.getByRole('checkbox')).toHaveCount(20);
  await expect(page.getByRole('button', { name: 'Confirm this revision and its disclosed gaps' })).toBeDisabled();
  await page.getByLabel('Application and integration owners reference', { exact: true }).fill('browser-owner-record');
  await page.getByLabel('Compute flavors interpretation', { exact: true }).selectOption('include');
  await page.getByLabel('Override reason and evidence reference', { exact: true }).fill('Operator review R1; portable compute requirement');
  await page.getByLabel('Compute flavors required', { exact: true }).check();
  await page.getByRole('button', { name: 'Save configuration review', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Revision saved');
  await page.reload();
  await expect(page.getByLabel('Application and integration owners reference', { exact: true })).toHaveValue('browser-owner-record');
  await expect(page.getByLabel('Compute flavors interpretation', { exact: true })).toHaveValue('include');
  await expect(page.getByRole('button', { name: 'Confirm this revision and its disclosed gaps' })).toBeEnabled();
  await page.getByRole('button', { name: 'Confirm this revision and its disclosed gaps' }).click();
  await expect(page.getByRole('status')).toContainText('Configuration review confirmed');
  await expect(page.getByRole('button', { name: 'Confirm this revision and its disclosed gaps' })).toBeDisabled();
  await page.setViewportSize({ width: 640, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBe(true);

  const author = await browser.newContext({ baseURL: process.env.CONSOLE_BASE_URL });
  await author.addCookies([fixture.author_cookie]);
  const watching = await author.newPage();
  await watching.goto(`${base}/generations/${fixture.generation}`);
  await expect(watching.getByRole('heading', { name: 'Observed resources' })).toBeVisible();
  const revoked = await request.post(`${fixture.governance_url}/v1/tenants/${fixture.tenant}/memberships`, {
    ignoreHTTPSErrors: true,
    headers: { Authorization: `Bearer ${fixture.console_workload}`, 'X-Console-Session': fixture.admin_token, 'Idempotency-Key': crypto.randomUUID() },
    data: { revision: fixture.membership.revision, subject: 'p03-author', role: 'author', state: 'revoked', site_id: null, environment: null, expires_at: null },
  });
  expect(revoked.status()).toBe(200);
  await expect(watching).toHaveURL(/\/account$/, { timeout: 30_000 });
  await watching.goBack();
  await expect(watching.getByRole('heading', { name: 'Observed resources' })).toHaveCount(0);
  expect(errors).toEqual([]);
  await author.close();
  await context.close();
});
