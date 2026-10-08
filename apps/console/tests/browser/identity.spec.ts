import { expect, test } from '@playwright/test';

test('administrator sign-in is keyboard accessible with password-manager fields', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('link', { name: 'Administrator sign-in' }).click();
  await expect(page).toHaveTitle('Administrator sign-in | Workload Mobility');
  await expect(page.getByLabel('Account')).toHaveValue('admin');
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('type', 'password');
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('autocomplete', 'current-password');
  await page.getByLabel('Password', { exact: true }).focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeFocused();
  await page.setViewportSize({ width: 375, height: 812 });
  expect(await page.locator('body').evaluate(element => element.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
