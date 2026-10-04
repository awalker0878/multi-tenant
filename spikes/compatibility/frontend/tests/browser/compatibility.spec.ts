import { expect, test } from '@playwright/test';

test('Laravel page hydrates and Inertia preserves the page through form validation', async ({ page, browser }, testInfo) => {
  const pageErrors: string[] = [];
  const documentRequests: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', request => {
    if (request.isNavigationRequest() && request.frame() === page.mainFrame()) {
      documentRequests.push(request.url());
    }
  });
  await testInfo.attach('browser-identity', {
    body: JSON.stringify({ engine: browser.browserType().name(), version: browser.version() }),
    contentType: 'application/json',
  });

  const initial = await page.goto('/compatibility');
  expect(initial?.status()).toBe(200);
  expect(initial?.headers()['content-type']).toContain('text/html');
  await expect(page.getByRole('heading', { name: 'Compatibility sample: 0' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Sample name' })).toBeVisible();

  // A full reload could still display the error; require the actual Inertia JSON exchange.
  const invalidResponse = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/compatibility'
    && response.request().headers()['x-inertia'] === 'true',
  );
  await page.getByRole('button', { name: 'Submit sample' }).click();
  const invalid = await invalidResponse;
  expect(invalid.status()).toBe(200);
  expect(invalid.headers()['x-inertia']).toBe('true');
  expect((await invalid.json()).component).toBe('Compatibility');
  await expect(page.getByRole('alert')).toContainText('required');
  await expect(page.getByRole('textbox', { name: 'Sample name' })).toHaveAttribute('aria-invalid', 'true');

  await page.getByRole('textbox', { name: 'Sample name' }).fill('Browser probe');
  const acceptedResponse = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/compatibility'
    && response.request().headers()['x-inertia'] === 'true',
  );
  await page.getByRole('button', { name: 'Submit sample' }).click();
  const accepted = await acceptedResponse;
  expect(accepted.status()).toBe(200);
  expect((await accepted.json()).props.notice).toBe('Compatibility request accepted');
  await expect(page.getByRole('status')).toHaveText('Compatibility request accepted');
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByRole('textbox', { name: 'Sample name' })).toHaveAttribute('aria-invalid', 'false');
  expect(documentRequests).toHaveLength(1);
  expect(pageErrors).toEqual([]);
});
