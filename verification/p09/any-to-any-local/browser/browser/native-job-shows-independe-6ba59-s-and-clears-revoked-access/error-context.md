# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: native-job.spec.ts >> shows independent stages, continues once after uncertainty, stops, and clears revoked access
- Location: tests/browser-p08/native-job.spec.ts:3:1

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByRole('alert')
Expected substring: "Refresh current state"
Error: strict mode violation: getByRole('alert') resolved to 2 elements:
    1) <p role="alert">Current state is unavailable. Controls are paused.</p> aka getByText('Current state is unavailable')
    2) <p role="alert">outcome uncertain. Refresh current state before a…</p> aka getByText('outcome uncertain. Refresh')

Call log:
  - Expect "toContainText" getByRole('alert') with timeout 5000ms
  - waiting for getByRole('alert')

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - link "Skip to workspace" [ref=e3] [cursor=pointer]:
    - /url: "#workspace-main"
  - generic [ref=e4]:
    - complementary [ref=e5]:
      - link "Workload Mobility home" [ref=e6] [cursor=pointer]:
        - /url: /account
        - generic [ref=e13]:
          - strong [ref=e14]: Workload Mobility
          - generic [ref=e15]: Enterprise hosting
      - navigation "Workspace navigation" [ref=e16]:
        - paragraph [ref=e17]: WORKSPACE
        - link "Your tenants" [ref=e18] [cursor=pointer]:
          - /url: /account
          - generic [aria-hidden] [ref=e19]: "01"
          - text: Your tenants
        - link "Applications" [ref=e20] [cursor=pointer]:
          - /url: /tenants/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/applications
          - generic [aria-hidden] [ref=e21]: "02"
          - text: Applications
        - link "Environments and domains" [ref=e22] [cursor=pointer]:
          - /url: /tenants/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/catalogue-references
          - generic [aria-hidden] [ref=e23]: "03"
          - text: Environments and domains
        - link "Observed inventory" [ref=e24] [cursor=pointer]:
          - /url: /tenants/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/inventory
          - generic [aria-hidden] [ref=e25]: "04"
          - text: Observed inventory
        - link "Tenant settings" [ref=e26] [cursor=pointer]:
          - /url: /tenants/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
          - generic [aria-hidden] [ref=e27]: "05"
          - text: Tenant settings
      - generic [ref=e28]:
        - paragraph [ref=e29]: Tenant workspace
        - code [ref=e30]: aaaaaaaa
        - button "Sign out" [ref=e31] [cursor=pointer]
    - generic [ref=e32]:
      - banner [ref=e33]:
        - generic [ref=e34]: OPERATIONS CONSOLE
        - generic [ref=e35]: Tenant scoped
      - main [ref=e36]:
        - generic [ref=e37]:
          - paragraph [ref=e38]: Workload Mobility / Workspace
          - heading "Native migration stages" [level=1] [ref=e39]
        - alert [ref=e40]: outcome uncertain. Refresh current state before another command.
        - button "Refresh current state" [ref=e41] [cursor=pointer]
        - generic [ref=e42]:
          - 'heading "Migration state: running" [level=2] [ref=e43]'
          - paragraph [ref=e44]: Revision 4. Each completed stage requires independent observations.
          - region "Measured migration progress" [ref=e45]:
            - heading "2 of 8 stages independently verified" [level=3] [ref=e46]
            - progressbar "Independently verified stages" [ref=e47]
            - paragraph [ref=e48]: Measured at 10/8/2026, 8:30:00 PM. Job admitted 10/8/2026, 8:26:40 PM.
            - paragraph [ref=e49]: Stage counts do not predict completion time. Elapsed time includes time awaiting independent verification.
            - generic [ref=e50]:
              - paragraph [ref=e51]:
                - strong [ref=e52]: "Retained transfer bytes:"
                - text: 1,073,741,824 bytes (1.00 GiB) across 1 completed disks.
              - paragraph [ref=e53]: Worker custody journal observed 10/8/2026, 8:30:00 PM. Artifact incomplete.
              - paragraph [ref=e54]: Only durably retained disk bytes count. Partial disk downloads and a completion estimate are unavailable.
          - table [ref=e56]:
            - caption [ref=e57]: Recorded stages
            - rowgroup [ref=e58]:
              - row [ref=e59]:
                - columnheader "Stage" [ref=e60]
                - columnheader "Effect" [ref=e61]
                - columnheader "Independent evidence" [ref=e62]
                - columnheader "Measured elapsed" [ref=e63]
                - columnheader "Last observation" [ref=e64]
            - rowgroup [ref=e65]:
              - row [ref=e66]:
                - cell "capture" [ref=e67]
                - cell "Dispatched" [ref=e68]
                - cell "Verified" [ref=e69]
                - cell "1 min 0 s" [ref=e70]
                - cell "10/8/2026, 8:27:50 PM" [ref=e71]
              - row [ref=e72]:
                - cell "export copy" [ref=e73]
                - cell "Dispatched" [ref=e74]
                - cell "Verified" [ref=e75]
                - cell "2 min 0 s" [ref=e76]
                - cell "10/8/2026, 8:30:00 PM" [ref=e77]
          - button "Stop migration" [ref=e79] [cursor=pointer]
          - paragraph [ref=e80]: "Stopping holds future effects. Recovery and production cutover require their approved plans. Native qualification: not established."
          - link "Review directional qualification and remaining blockers" [ref=e81] [cursor=pointer]:
            - /url: /tenants/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/applications/cccccccc-cccc-4ccc-8ccc-cccccccccccc/environments/dddddddd-dddd-4ddd-8ddd-dddddddddddd/planning/migration-support/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb
      - contentinfo [ref=e82]:
        - text: Workload Mobility
        - generic [ref=e83]: Provision · Migrate · Verify
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { nativeRoute } from './native-fixture';
  3  | test('shows independent stages, continues once after uncertainty, stops, and clears revoked access', async ({ page, request }, info) => {
  4  |   await request.post('/__native', { data: { reset: true } });
  5  |   await page.goto(nativeRoute);
  6  |   await expect(page.getByRole('heading', { name: 'Native migration stages', exact: true })).toBeVisible();
  7  |   await expect(page.getByText('Awaiting verification', { exact: true })).toBeVisible();
  8  |   await expect(page.getByRole('heading', { name: '1 of 8 stages independently verified', exact: true })).toBeVisible();
  9  |   await expect(page.getByRole('table')).toContainText('1 min 0 s');
  10 |   await expect(page.getByText(/1,073,741,824 bytes \(1.00 GiB\)/)).toBeVisible();
  11 |   await expect(page.getByRole('progressbar', { name: 'Independently verified stages' })).toHaveAttribute('value', '1');
  12 |   await request.post('/__native', { data: { uncertain: true } });
  13 |   await page.getByRole('button', { name: 'Continue immutable download', exact: true }).click();
> 14 |   await expect(page.getByRole('alert')).toContainText('Refresh current state');
     |                                         ^ Error: expect(locator).toContainText(expected) failed
  15 |   await expect(page.getByRole('heading', { name: 'Migration state: running', exact: true })).toBeVisible();
  16 |   await expect(page.getByRole('heading', { name: '2 of 8 stages independently verified', exact: true })).toBeVisible();
  17 |   await expect(page.getByRole('button', { name: 'Continue immutable download', exact: true })).toHaveCount(0);
  18 |   expect((await (await request.get('/__native')).json()).posts).toEqual([{ action: 'continue-transfer', expected_revision: 3 }]);
  19 |   await page.getByRole('button', { name: 'Stop migration', exact: true }).click();
  20 |   await expect(page.getByRole('heading', { name: 'Migration state: stopped', exact: true })).toBeVisible();
  21 |   await page.screenshot({ path: info.outputPath('native-job.png'), fullPage: true });
  22 |   await request.post('/__native', { data: { access: 403 } });
  23 |   await page.getByRole('button', { name: 'Refresh current state', exact: true }).click();
  24 |   await expect(page).toHaveURL(/\/account$/);
  25 | });
  26 | 
  27 | test('rejects stale revisions and keeps read-only operators from sending native controls', async ({ page, request }) => {
  28 |   await request.post('/__native', { data: { reset: true, control_allowed: false } });
  29 |   await page.goto(nativeRoute);
  30 |   await expect(page.getByRole('button', { name: 'Stop migration', exact: true })).toHaveCount(0);
  31 |   await expect(page.getByRole('button', { name: 'Continue immutable download', exact: true })).toHaveCount(0);
  32 |   await request.post('/__native', { data: { revision: 2 } });
  33 |   await page.getByRole('button', { name: 'Refresh current state', exact: true }).click();
  34 |   await expect(page.getByRole('alert')).toContainText('Current state is unavailable');
  35 |   await expect(page.getByText('Revision 3. Each completed stage requires independent observations.')).toBeVisible();
  36 |   expect((await (await request.get('/__native')).json()).posts).toEqual([]);
  37 | });
  38 | 
```