# Workload Mobility console

The console provides tenant-scoped application, environment, provisioning,
migration, approval and recovery journeys through the owning service APIs.
Laravel/Inertia owns presentation and browser sessions; Governance, Inventory,
Planning, Lifecycle and Assurance retain their records and authorization.

The shared Workload Mobility theme supplies navy workspace navigation, teal
controls, a consistent brand mark and responsive layouts. Site administrators
reach **Operator readiness** from **Observed inventory → Site inventory**.

## Site commissioning

1. Enroll approved connections in **Site inventory**. Trust policies and scoped
   secret-store records must already exist under their owning administrators.
2. Use **Environment configuration** to pull native API findings and review
   required capabilities. Supply only the configuration references that cannot
   be discovered from the APIs.
3. Use **Operator readiness** to collect the 32 account, trust, execution,
   recovery, target and service-handover inputs. Save partial drafts and download
   the saved, revision-bound packet for the commissioning team.
4. Review workload profiles and datasets, prepare migration groups, review exact
   plans and schedule approved migration campaigns through their existing pages.

A saved reference is not verified evidence. API discovery, operator-input
collection, native qualification and execution approval remain distinct. The
console never mounts a credential or grants native authority from these inputs.
Supply protected record identifiers, not passwords, tokens or private keys.

| Site route suffix | Purpose |
| --- | --- |
| `/configuration` | API findings, capability requirements and saved environment review |
| `/operator-inputs` | Owner references, operating targets and missing-input checklist |
| `/operator-inputs/download` | Freshly authorized JSON handoff for the saved packet |
| `/migration` | Workload method, dataset and application-owner review |
| `/migration-fleet` | Source inventory, grouping and bulk preparation |

Site routes are under `/tenants/{tenant}/inventory/sites/{site}`. Operator-input
reads, saves, polling and exports require current site administration. Saves use
CSRF protection, revision preconditions and idempotent command identities. After
an uncertain response the UI freezes edits until the same command is recovered.
Tenant changes/revocation clear the previous browser context. Authenticated pages
and downloads are private and non-cacheable. Browser storage holds no input drafts.

## Deployment

Deploy the matching Inventory service and apply
`services/inventory/migrations/007_operator_inputs.sql` through the existing
migration owner before enabling this increment. The runtime role has immutable
SELECT/INSERT access. The additive Inventory 1.4 contract preserves all published
1.3 operations and schemas. Existing native readiness and approval controls remain
in force. Merge to main does not deploy an installation.

Production requires HTTPS, protected generated keys, secure session cookies and
the commissioned service dependencies. The loopback development server does not
establish the production ingress or multi-replica architecture.

## Install and verify

Use the repository's accepted PHP 8.5.11, Composer 2.10.3, Node 24.19.0 and npm 11
family. Dependencies are owned and locked by this application.

```sh
composer install --no-interaction --no-progress --prefer-dist
composer check-platform-reqs
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm run test:boundaries
npm run build
composer test:format
composer test:types
composer test:architecture
composer test:canaries
composer test
npx playwright install --with-deps --only-shell chromium
npx playwright test --config tests/browser-p08/playwright.config.ts
```

The P08 browser suite renders actual Vue/Inertia pages with an isolated HTTP
fixture. It covers migration review, inventory grouping, campaigns and operator
inputs, including desktop/mobile layout, unchanged retry, stale edits and revoked
access. It also checks campaign dependency cleanup, destination selection after
site edits, bounded support refreshes, and readiness evidence refreshes against
the matching saved input revision. Inventory's separate PostgreSQL tests cover owner persistence and tenant
isolation. Native platform qualification and independent receiving review require
their original live observations; neither is inferred from the browser suite.

See the [console specification](../../docs/services/console.md),
[frontend standard](../../docs/engineering/frontend.md) and
[operator-input handoff](../../docs/implementation/console-operator-readiness.md).
