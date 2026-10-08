import { test, expect } from '@playwright/test';

test('holds qualification after a stalled support refresh and recovers on the next poll', async ({ page }) => {
  const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  const platforms = ['vmware', 'openstack', 'ahv'];
  const support = { tranche_sha256: 'a'.repeat(64), release_sha256: 'b'.repeat(64), directions: platforms.flatMap(source => platforms.map(target => ({ direction: `${source}->${target}`, state: 'selected', routes: source === 'vmware' && target === 'openstack' ? [{ route_id: id, guest: 'Linux', guest_profile_sha256: 'c'.repeat(64), method: 'VM_COLD_EXPORT', source: { platform: source, installation_id: id, versions: {} }, target: { platform: target, installation_id: id, versions: {} }, constraints: {}, exclusions: [], blockers: [], native_qualified: true, operationally_accepted: true }] : [] }))) };
  const descriptor = { component: 'planning/MigrationSupport', props: { tenantId: id, siteId: id, applicationId: id, environment: id, support }, url: '/__support', version: null, clearHistory: false, encryptHistory: false };
  const data = JSON.stringify(descriptor).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
  await page.route('**/__support', route => route.fulfill({ contentType: 'text/html', body: `<!doctype html><html><body><div id="app" data-page="${data}"></div><script type="module" src="/tests/browser-p08/entry.ts"></script></body></html>` }));
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let started!: () => void;
  const pending = new Promise<void>(resolve => { started = resolve; });
  let requests = 0;
  await page.route('**/migration-support/*/status', async route => {
    requests++;
    if (requests === 1) { started(); await gate; }
    await route.fulfill({ json: { available: true, support } });
  });
  await page.clock.install();
  await page.goto('/__support');
  await expect(page.getByText('Native qualification: Accepted', { exact: true })).toBeVisible();
  await page.clock.fastForward(15_000);
  await pending;
  await page.clock.fastForward(12_000);
  await expect(page.getByRole('alert')).toContainText('Displayed results are stale');
  await expect(page.getByText('Native qualification: Held', { exact: true })).toBeVisible();
  await expect(page.getByText('Operating acceptance: Pending', { exact: true })).toBeVisible();
  release();
  await page.clock.fastForward(15_000);
  await expect(page.getByText('Native qualification: Accepted', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
