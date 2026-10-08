import { test, expect } from '@playwright/test';

test('invalidates selected endpoints and ignores late discovery after a site edit', async ({ page }) => {
  const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  const otherSite = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
  const descriptor = { component: 'planning/Workspace', props: { tenantId: id, applicationId: id, environment: id, revisionId: id, record: null, sites: [], notice: null }, url: '/__planning', version: null, clearHistory: false, encryptHistory: false };
  const data = JSON.stringify(descriptor).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
  await page.route('**/__planning', route => route.fulfill({ contentType: 'text/html', body: `<!doctype html><html><body><div id="app" data-page="${data}"></div><script type="module" src="/tests/browser-p08/entry.ts"></script></body></html>` }));
  const endpoint = { endpoint_id: id, generation_id: id, label: 'Site A endpoint', platform: 'openstack', reason: null };
  await page.route('**/destinations/*', route => route.fulfill({ json: { items: [endpoint] } }));
  await page.goto('/__planning');
  const site = page.getByLabel('Approved site ID').first();
  const selection = page.getByRole('combobox', { name: 'Endpoint', exact: true }).first();
  await site.fill(id);
  await page.getByRole('button', { name: 'Load collected endpoints' }).first().click();
  await expect(selection.locator('option')).toHaveCount(2);
  await selection.selectOption(id);
  await site.fill(otherSite);
  await expect(selection).toHaveValue('');
  await expect(selection.locator('option')).toHaveCount(1);

  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let started!: () => void;
  const pending = new Promise<void>(resolve => { started = resolve; });
  await page.route('**/destinations/*', async route => { started(); await gate; await route.fulfill({ json: { items: [endpoint] } }); });
  await site.fill(id);
  await page.getByRole('button', { name: 'Load collected endpoints' }).first().click();
  await pending;
  const cancelled = page.waitForEvent('requestfailed', request => request.url().includes('/destinations/'));
  await site.fill(otherSite);
  await cancelled;
  release();
  await expect(selection.locator('option')).toHaveCount(1);
  await expect(selection).toHaveValue('');
});
