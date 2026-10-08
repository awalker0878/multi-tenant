import { test, expect } from '@playwright/test';
const base = '/tenants/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/inventory/sites/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/migration';

test('selects each source and destination direction without assuming a VMware source', async ({ page, request }) => {
  for (const sourcePlatform of ['vmware', 'openstack', 'ahv']) {
    for (const destinationPlatform of ['vmware', 'openstack', 'ahv']) {
      await request.post('/__fixture', { data: { reset: true, vmware: destinationPlatform === 'vmware', ahv: destinationPlatform === 'ahv', source_platform: sourcePlatform } });
      const state = await (await request.get('/__fixture')).json();
      await page.goto(base);
      await page.getByLabel('Source VM profile').selectOption(state.workspace.profiles[0].id);
      await page.getByLabel('Destination profile').selectOption(state.workspace.profiles[1].id);
      await expect(page.getByLabel('Source VM profile').locator('option:checked')).toContainText(sourcePlatform);
      await expect(page.getByLabel('Destination profile').locator('option:checked')).toContainText(destinationPlatform);
      await expect(page.getByRole('button', { name: 'Save migration review', exact: true })).toBeDisabled();
      if (destinationPlatform !== 'openstack') {
        await expect(page.getByLabel('Explicit migration method')).toHaveValue('VM_COLD_EXPORT');
        await expect(page.getByText(`${destinationPlatform === 'ahv' ? 'AHV' : 'VMware'} destination mapping`, { exact: true })).toBeVisible();
      }
    }
  }
});

test('maps every observed disk, preserves uncertain commands, confirms exact review, and clears revoked access', async ({ page, request }, info) => {
  await request.post('/__fixture', { data: { reset: true } });
  const state = await (await request.get('/__fixture')).json();
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await expect(page.getByRole('heading', { name: 'Migration readiness review', exact: true })).toBeFocused();
  await expect(page.getByLabel('Explicit migration method')).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Confirm migration review', exact: true })).toBeDisabled();
  await page.getByLabel('Source VM profile').selectOption(state.workspace.profiles[0].id);
  await page.getByLabel('Destination profile').selectOption(state.workspace.profiles[1].id);
  await page.getByLabel('Explicit migration method').selectOption('VM_COLD_EXPORT');
  await expect(page.getByRole('button', { name: 'Save migration review', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Add dataset', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill('Application and attachments');
  await page.getByLabel('Consistency group', { exact: true }).fill('all-data');
  await page.getByLabel('Mounts or dataset paths (one per line)').fill('/\n/data');
  await page.getByLabel('Correctness check reference').fill('synthetic-check-only');
  for (const disk of state.workspace.profiles[0].facts.disks) await page.getByLabel(`Disk ${disk.key}`, { exact: true }).check();
  await expect(page.getByText('Mapping required', { exact: true })).toHaveCount(0);
  for (const field of state.workspace.owner_fields.filter((f: string) => f !== 'delta_protocol')) await page.getByLabel(field.replaceAll('_', ' '), { exact: true }).fill('synthetic-owner-reference');
  await page.getByLabel('Application owner ID').fill('cccccccc-cccc-4ccc-8ccc-cccccccccccc');
  await page.getByLabel('Acceptance record SHA-256').fill('c'.repeat(64));
  await page.getByLabel('Maximum outage (seconds)').fill('300');
  await page.getByLabel('Maximum data loss (bytes)').fill('0');
  await page.getByRole('button', { name: 'Add reasoned interpretation' }).click();
  await page.getByLabel('Interpretation', { exact: true }).fill('Quiesce application before capture');
  await page.getByLabel('Reason and evidence', { exact: true }).fill('Application owner decision R1');
  await request.post('/__fixture', { data: { uncertain: true } });
  await page.getByRole('button', { name: 'Save migration review', exact: true }).click();
  await expect(page.getByRole('alert')).toBeFocused();
  await expect(page.getByRole('alert')).toContainText('uncertain');
  await expect(page.getByLabel('Name', { exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Retry unchanged command', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Migration review saved.');
  const posted = (await (await request.get('/__fixture')).json()).posts;
  expect(posted).toHaveLength(2); expect(posted[0]).toEqual(posted[1]);
  await expect(page.getByRole('button', { name: 'Confirm migration review', exact: true })).toBeEnabled();
  await page.getByLabel('Name', { exact: true }).fill('Changed after saving');
  await expect(page.getByRole('button', { name: 'Confirm migration review', exact: true })).toBeDisabled();
  await page.reload();
  await page.getByRole('button', { name: 'Confirm migration review', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Migration review confirmed.');
  await expect(page.getByRole('button', { name: 'Confirm migration review', exact: true })).toBeDisabled();
  await expect(page.locator('img')).toHaveCount(0);
  await page.screenshot({ path: info.outputPath('migration-review.png'), fullPage: true });
  await page.setViewportSize({ width: 640, height: 800 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBe(true);
  await request.post('/__fixture', { data: { expire: true } });
  await page.reload();
  await expect(page.getByText('Revision 1 · Review required', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm migration review', exact: true })).toBeDisabled();
  await request.post('/__fixture', { data: { access: 403 } });
  await expect(page).toHaveURL(/\/account$/, { timeout: 25_000 });
  expect(errors).toEqual([]);
});

test('selects AHV resources and saves complete quarantine mappings without authorizing migration', async ({ page, request }, info) => {
  await request.post('/__fixture', { data: { reset: true, ahv: true } });
  const state = await (await request.get('/__fixture')).json();
  const source = state.workspace.profiles[0], target = state.workspace.profiles[1];
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(base);
  await page.getByLabel('Source VM profile').selectOption(source.id);
  await page.getByRole('combobox', { name: 'Destination profile', exact: true }).selectOption(target.id);
  await expect(page.getByLabel('Explicit migration method')).toHaveValue('VM_COLD_EXPORT');
  await expect(page.getByText('AHV destination mapping', { exact: true })).toBeVisible();
  await page.getByRole('combobox', { name: 'Storage container', exact: true }).selectOption(target.facts.storage_containers[0].extId);
  await page.getByLabel('Migration: Quarantine', { exact: true }).check();
  await page.getByLabel('Synthetic isolation · ENFORCE', { exact: true }).check();
  for (const nic of source.facts.nics) {
    await page.getByRole('combobox', { name: `NIC ${nic.key} quarantine subnet`, exact: true }).selectOption(target.facts.subnets[0].extId);
    await page.getByRole('combobox', { name: `NIC ${nic.key} production subnet`, exact: true }).selectOption(target.facts.subnets[1].extId);
  }
  await page.getByRole('button', { name: 'Add dataset', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill('All application data');
  await page.getByLabel('Consistency group', { exact: true }).fill('app');
  await page.getByLabel('Mounts or dataset paths (one per line)').fill('/');
  await page.getByLabel('Correctness check reference').fill('synthetic-only');
  for (const disk of source.facts.disks) await page.getByLabel(`Disk ${disk.key}`, { exact: true }).check();
  for (const field of state.workspace.owner_fields.filter((f: string) => f !== 'delta_protocol')) await page.getByLabel(field.replaceAll('_', ' '), { exact: true }).fill('owner-approved-reference');
  await page.getByLabel('Application owner ID').fill('cccccccc-cccc-4ccc-8ccc-cccccccccccc');
  await page.getByLabel('Acceptance record SHA-256').fill('c'.repeat(64));
  await page.getByLabel('Maximum outage (seconds)').fill('300');
  await page.getByLabel('Maximum data loss (bytes)').fill('0');
  await page.getByRole('button', { name: 'Save migration review', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Migration review saved.');
  const saved = (await (await request.get('/__fixture')).json()).posts[0].review;
  expect(saved.destination.project_id).toBe(target.facts.project_id);
  expect(saved.destination.disks).toHaveLength(source.facts.disks.length);
  expect(saved.destination.nics).toHaveLength(source.facts.nics.length);
  expect(saved.destination.nics.every((n: any) => n.quarantine_subnet_id !== n.production_subnet_id)).toBe(true);
  await expect(page.getByRole('button', { name: 'Confirm migration review', exact: true })).toBeEnabled();
  await page.screenshot({ path: info.outputPath('ahv-destination.png'), fullPage: true });
  expect(errors).toEqual([]);
});

test('maps VMware placement, every disk and isolated NICs while preserving source firmware', async ({ page, request }, info) => {
  await request.post('/__fixture', { data: { reset: true, vmware: true } });
  const state = await (await request.get('/__fixture')).json();
  const source = state.workspace.profiles[0], target = state.workspace.profiles[1];
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto(base);
  await page.getByLabel('Source VM profile').selectOption(source.id);
  await page.getByRole('combobox', { name: 'Destination profile', exact: true }).selectOption(target.id);
  await expect(page.getByLabel('Explicit migration method')).toHaveValue('VM_COLD_EXPORT');
  await expect(page.getByText('VMware destination mapping', { exact: true })).toBeVisible();
  for (const [label, plural, key] of [['VM folder', 'folders', 'folder'], ['Resource pool', 'resource_pools', 'resource_pool'], ['Host', 'hosts', 'host'], ['Datastore', 'datastores', 'datastore']]) {
    await page.getByRole('combobox', { name: label, exact: true }).selectOption(target.facts[plural][0][key]);
  }
  await page.getByLabel('Guest compatibility ID', { exact: true }).fill('rhel9_64Guest');
  await page.getByLabel('Hardware compatibility', { exact: true }).fill('vmx-21');
  for (const nic of source.facts.nics) {
    await page.getByRole('combobox', { name: `NIC ${nic.key} quarantine network`, exact: true }).selectOption('network-1');
    await page.getByRole('combobox', { name: `NIC ${nic.key} production network`, exact: true }).selectOption('network-2');
  }
  await page.getByRole('button', { name: 'Add dataset', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill('Application');
  await page.getByLabel('Consistency group', { exact: true }).fill('all-data');
  await page.getByLabel('Mounts or dataset paths (one per line)').fill('/');
  await page.getByLabel('Correctness check reference').fill('synthetic-only');
  for (const disk of source.facts.disks) await page.getByLabel(`Disk ${disk.key}`, { exact: true }).check();
  for (const field of state.workspace.owner_fields.filter((f: string) => f !== 'delta_protocol')) await page.getByLabel(field.replaceAll('_', ' '), { exact: true }).fill('reviewed-reference');
  await expect(page.getByLabel('delta protocol', { exact: true })).toBeDisabled();
  await page.getByLabel('Application owner ID').fill('cccccccc-cccc-4ccc-8ccc-cccccccccccc');
  await page.getByLabel('Acceptance record SHA-256').fill('c'.repeat(64));
  await page.getByLabel('Maximum outage (seconds)').fill('0');
  await page.getByLabel('Maximum data loss (bytes)').fill('0');
  await page.getByRole('button', { name: 'Save migration review', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Migration review saved.');
  const review = (await (await request.get('/__fixture')).json()).posts[0].review;
  expect(review.destination.platform).toBe('vmware'); expect(review.destination.firmware).toBe('efi');
  expect(review.destination.disks).toHaveLength(source.facts.disks.length);
  expect(review.destination.nics[0].quarantine_network_id).not.toBe(review.destination.nics[0].production_network_id);
  expect(review.owner_inputs.delta_protocol).toBe(''); expect(review.objectives.max_outage_seconds).toBe(0);
  await page.reload();
  await page.getByRole('button', { name: 'Confirm migration review', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Migration review confirmed.');
  await page.screenshot({ path: info.outputPath('vmware-destination.png'), fullPage: true });
  expect(errors).toEqual([]);
});
