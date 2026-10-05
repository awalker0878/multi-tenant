import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ browser, browserName }, testInfo) => {
  testInfo.annotations.push(
    { type: 'browser-engine', description: browserName },
    { type: 'browser-version', description: browser.version() },
  );
});

test('deployment credential requires a change, survives reload and cannot be reused', async ({ page }) => {
  const path = process.env.P02_BOOTSTRAP_FILE;
  if (!path) throw new Error('The isolated P02 runner must supply its private credential fixture.');
  const credential = JSON.parse(readFileSync(path, 'utf8')) as { temporary: string; replacement: string };
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/setup');
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Password', { exact: true }).fill(credential.temporary);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Change your password' })).toBeVisible();
  await page.goto('/setup');
  await expect(page).toHaveURL(/\/password$/);
  await page.getByLabel('Current password', { exact: true }).fill(credential.temporary);
  await page.getByLabel('New password', { exact: true }).fill(credential.replacement);
  await page.getByLabel('Confirm new password', { exact: true }).fill(credential.replacement);
  await page.getByRole('button', { name: 'Change password', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Installation setup' })).toBeVisible();
  await page.reload();
  await expect(page.getByText('Changed', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Password', { exact: true }).fill(credential.temporary);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('could not be verified');
  await expect(page.getByLabel('Password', { exact: true })).toBeEmpty();
  await page.getByLabel('Password', { exact: true }).fill(credential.replacement);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Installation setup' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('console configuration verifies HTTPS federation and enforces tenant revocation across browsers', async ({ page, browser }) => {
  const path = process.env.P02_BOOTSTRAP_FILE;
  if (!path) throw new Error('The isolated P02 runner must supply its private fixture.');
  const fixture = JSON.parse(readFileSync(path, 'utf8')) as {
    replacement: string; provider: { issuer: string; client_id: string; client_secret: string; private_networks: string };
  };
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/login');
  await page.getByLabel('Password', { exact: true }).fill(fixture.replacement);
  await page.getByRole('button', { name: 'Sign in', exact: true }).press('Enter');
  await expect(page).toHaveURL(/\/setup$/);
  await page.getByLabel('Issuer URL', { exact: true }).fill(fixture.provider.issuer);
  await page.getByLabel('Client ID', { exact: true }).fill(fixture.provider.client_id);
  await page.getByLabel('Client secret', { exact: true }).fill(fixture.provider.client_secret);
  await page.getByLabel('Federated administrator subject', { exact: true }).fill('p02-admin');
  await page.getByLabel('Private provider networks (optional)', { exact: true }).fill(fixture.provider.private_networks);
  await page.getByRole('button', { name: 'Save provider settings' }).press('Enter');
  await expect(page.getByRole('status')).toContainText('Settings saved');
  await expect(page.getByLabel('Client secret', { exact: true })).toBeEmpty();
  expect(await page.content()).not.toContain(fixture.provider.client_secret);
  await page.getByRole('button', { name: 'Test administrator sign-in' }).press('Enter');
  await expect(page.getByRole('heading', { name: 'Disposable identity provider' })).toBeVisible();
  await page.getByLabel('Fixture subject').selectOption('p02-outsider');
  await page.getByRole('button', { name: 'Continue to console' }).press('Enter');
  await expect(page).toHaveURL(/\/setup$/);
  await expect(page.getByRole('status')).toContainText('Sign-in was not verified');
  await expect(page.getByRole('button', { name: 'Activate single sign-on' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Test administrator sign-in' }).press('Enter');
  await page.getByRole('button', { name: 'Continue to console' }).press('Enter');
  await expect(page).toHaveURL(/\/setup$/);
  await expect(page.getByRole('status')).toContainText('Federated administrator verified');
  await page.getByRole('button', { name: 'Activate single sign-on' }).press('Enter');
  await expect(page.getByText('External single sign-on: Active', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Your tenants' }).click();
  for (const name of ['P02 Tenant A', 'P02 Tenant B']) {
    await page.getByLabel('Tenant name', { exact: true }).fill(name);
    await page.getByLabel('Initial administrator subject').fill('p02-admin');
    await page.getByRole('button', { name: 'Create tenant', exact: true }).click();
    await expect(page.getByRole('link', { name, exact: true })).toBeVisible();
  }
  const tenantB = await page.getByRole('link', { name: 'P02 Tenant B', exact: true }).getAttribute('href');
  await page.getByRole('link', { name: 'P02 Tenant A', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'P02 Tenant A', exact: true })).toBeVisible();
  const tenantA = new URL(page.url()).pathname;
  await page.getByLabel('Member subject', { exact: true }).fill('p02-reader');
  await page.getByRole('button', { name: 'Add membership', exact: true }).click();
  await expect(page.getByRole('listitem').filter({ hasText: 'p02-reader' })).toBeVisible();
  await page.getByLabel('vCPU', { exact: true }).fill('12');
  await page.getByRole('button', { name: 'Save quota', exact: true }).click();
  await page.reload();
  await expect(page.getByLabel('vCPU', { exact: true })).toHaveValue('12');

  // Hold one complete old-tenant response until a newer navigation finishes.
  await page.getByRole('link', { name: 'All your tenants' }).click();
  let releaseOld!: () => void;
  let oldReady!: () => void;
  let oldFinished!: () => void;
  const held = new Promise<void>(resolve => { releaseOld = resolve; });
  const ready = new Promise<void>(resolve => { oldReady = resolve; });
  const finished = new Promise<void>(resolve => { oldFinished = resolve; });
  await page.route(`**${tenantA}`, async route => {
    const response = await route.fetch();
    oldReady();
    await held;
    try { await route.fulfill({ response }); }
    finally { oldFinished(); }
  });
  await page.getByRole('link', { name: 'P02 Tenant A', exact: true }).click();
  await ready;
  await page.getByRole('link', { name: 'P02 Tenant B', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'P02 Tenant B', exact: true })).toBeVisible();
  releaseOld();
  await finished;
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page.getByRole('heading', { name: 'P02 Tenant B', exact: true })).toBeFocused();
  await expect(page.getByLabel('vCPU', { exact: true })).toHaveValue('0');
  await page.unroute(`**${tenantA}`);
  await page.goto(tenantA);

  const sibling = await page.context().newPage();
  sibling.on('pageerror', error => errors.push(error.message));
  await sibling.goto(tenantB!);
  await expect(sibling.getByRole('heading', { name: 'P02 Tenant B', exact: true })).toBeVisible();
  await page.getByLabel('Member subject', { exact: true }).fill('unsaved-tenant-a-draft');
  await expect(sibling.getByLabel('Member subject', { exact: true })).toBeEmpty();

  const readerContext = await browser.newContext({ baseURL: process.env.CONSOLE_BASE_URL, ignoreHTTPSErrors: true });
  try {
    const reader = await readerContext.newPage();
    reader.on('pageerror', error => errors.push(error.message));
    await reader.goto('/login');
    await reader.getByRole('button', { name: 'Sign in with your identity provider' }).click();
    await reader.getByLabel('Fixture subject').selectOption('p02-reader');
    await reader.getByRole('button', { name: 'Continue to console' }).click();
    await expect(reader).toHaveURL(/\/account$/);
    await expect(reader.getByRole('link', { name: 'P02 Tenant A', exact: true })).toBeVisible();
    await expect(reader.getByText('P02 Tenant B', { exact: true })).toHaveCount(0);
    await reader.goto(tenantB!);
    await expect(reader).toHaveURL(/\/account$/);
    await expect(reader.getByRole('status')).toContainText('unavailable or your access has changed');
    await reader.goto(tenantA + '?role=tenant_admin');
    await expect(reader.getByRole('heading', { name: 'P02 Tenant A', exact: true })).toBeVisible();
    await expect(reader.getByRole('heading', { name: 'Memberships', exact: true })).toHaveCount(0);
    await page.getByRole('listitem').filter({ hasText: 'p02-reader' }).getByRole('button', { name: 'Edit membership' }).click();
    await page.getByLabel('Membership state', { exact: true }).selectOption('revoked');
    await page.getByRole('button', { name: 'Update membership', exact: true }).click();
    await expect(page.getByRole('listitem').filter({ hasText: 'p02-reader' })).toContainText('revoked');
    await reader.reload();
    await expect(reader).toHaveURL(/\/account$/);
    await expect(reader.getByText('You have no current tenant memberships. Contact your tenant administrator.', { exact: true })).toBeVisible();
  } finally {
    await readerContext.close();
  }
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(sibling).toHaveURL(/\/login$/);
  await expect(sibling.getByRole('heading', { name: 'P02 Tenant B', exact: true })).toHaveCount(0);
  await sibling.close();
  await page.getByLabel('Password', { exact: true }).fill(fixture.replacement);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('could not be verified');
  await page.getByRole('button', { name: 'Sign in with your identity provider' }).click();
  await page.getByRole('button', { name: 'Continue to console' }).click();
  await expect(page).toHaveURL(/\/setup$/);
  await expect(page.getByText('External single sign-on: Active', { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
