import { test, expect } from '@playwright/test';

test('removes dependencies on a removed campaign member before saving', async ({ page, request }) => {
  await request.post('/__campaign', { data: { reset: true } });
  const initial = await (await request.get('/__campaign')).json();
  const otherPlan = 'ffffffff-ffff-4fff-8fff-ffffffffffff';
  await page.route(`**${initial.base}/plans/*`, async route => {
    await route.fulfill({ json: { ...initial.plan, plan_id: route.request().url().split('/').at(-1) } });
  });
  await page.goto(initial.base);
  await page.getByLabel('Campaign name', { exact: true }).fill('Dependency edit');
  for (const plan of [initial.plan.plan_id, otherPlan]) {
    await page.getByLabel('Reviewed plan reference', { exact: true }).fill(plan);
    await page.getByRole('button', { name: 'Load reviewed plan', exact: true }).click();
  }
  const firstMember = await page.getByLabel('Wait for completed migrations').nth(1).locator('option').getAttribute('value');
  await page.getByLabel('Wait for completed migrations').nth(1).selectOption(firstMember!);
  await page.getByRole('button', { name: 'Remove plan', exact: true }).first().click();
  await page.getByLabel('Independent approval reference').fill('eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee');
  await page.getByRole('button', { name: 'Create draft campaign', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Start schedule', exact: true })).toBeVisible();
  const saved = await (await request.get('/__campaign')).json();
  expect(saved.posts[0].body.members).toHaveLength(1);
  expect(saved.posts[0].body.members[0].plan_id).toBe(otherPlan);
  expect(saved.posts[0].body.members[0].depends_on).toEqual([]);
});

test('schedules measured migrations, recovers a lost receipt, pauses, and clears revoked access', async ({ page, request }, info) => {
  await request.post('/__campaign', { data: { reset: true } });
  const initial = await (await request.get('/__campaign')).json();
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto(initial.base);
  await page.getByLabel('Campaign name', { exact: true }).fill('Ottawa wave <img src=x onerror=alert(1)>');
  await page.getByLabel('Reviewed plan reference', { exact: true }).fill(initial.plan.plan_id);
  await page.getByRole('button', { name: 'Load reviewed plan', exact: true }).click();
  await page.getByLabel('Independent approval reference').fill('eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee');
  await request.post('/__campaign', { data: { uncertain: true } });
  await page.getByRole('button', { name: 'Create draft campaign', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('uncertain');
  await expect(page.getByLabel('Campaign name', { exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Recover unchanged command receipt' }).click();
  await expect(page.getByRole('button', { name: 'Start schedule', exact: true })).toBeVisible();
  const saved = await (await request.get('/__campaign')).json();
  expect(saved.posts).toHaveLength(2); expect(saved.posts[0]).toEqual(saved.posts[1]);
  expect(saved.posts[0].body.members[0]).not.toHaveProperty('sizes');
  expect(saved.posts[0].body.members[0]).not.toHaveProperty('demands');
  await expect(page.locator('img')).toHaveCount(0);
  await expect(page.getByRole('table')).toContainText('Measurement required');
  await page.getByRole('button', { name: 'Start schedule', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Pause campaign', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Pause campaign', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Resume schedule', exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath('migration-campaign.png'), fullPage: true });
  await request.post('/__campaign', { data: { access: 403 } });
  await expect(page).toHaveURL(/\/account$/, { timeout: 25000 });
  expect(errors).toEqual([]);
});
