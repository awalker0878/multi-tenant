# P04 Inventory implementation

The user authorized continued P04 development on 2026-10-06. This record tracks
P04.01–P04.05; it does not supply the actual native inputs or G04 decision.

## Persistence and trust increment

Inventory now owns enrolled endpoint revisions, durable collection jobs, fenced
page leases, immutable page/observation history, command receipts, audit/outbox
facts and matching proposals. PostgreSQL is the only persistent state owner.
Runtime cannot rewrite accepted observations, receipts, audit or event facts.
Two complete absent generations are required before an observation is tombstoned.
Changed/reused or unavailable incarnation identities hold matching. Desired intent,
capacity reservations and native ownership are never inferred from these records.

The separately mounted site policy binds tenant, site, current owner, worker
fingerprint, native epoch/scope, approved TLS destinations/addresses, credential
references, installed declarations, permission-coverage reference and request
budgets. Enrollment cannot add destinations. Renew/revoke uses an expected revision;
both fence active work. Worker dispatch and result acceptance consult current
Governance owner/tenant admission as well as the live enrollment policy.

The queue applies an aggregate endpoint request interval, endpoint concurrency,
tenant concurrency, a 20-job tenant backlog, a 30-second page lease, three failed
attempts, a one-hour collection deadline, 100 pages and 10,000 observed resources.
Competing tenants rotate per endpoint. Limits are initial engineering bounds;
actual site budgets remain operating inputs. Expired pages cannot refresh a
generation. Native retry continuations contain identifiers, never returned URLs.

## Qualification in progress

The new [P04 workflow](../../.github/workflows/p04-inventory.yml) executes real
PostgreSQL/TLS, immutable-role, competing-tenant, restart, revocation and hostile
page cases and retains logs/source bindings. Local unit checks run in the locked
package. The current local user namespace maps only UID 0; PostgreSQL correctly
rejects that process identity, so the database campaign runs on the unprivileged
hosted runner. This is an environment limitation, not a passing database result.

Worker, Console, published contracts and integrated acceptance continue in the
next increments. G04 requires actual installed OpenStack/VMware tuple, endpoint,
trust, read privilege/scope and independent before/after observations. None has
been supplied, and no synthetic result qualifies those platforms. All eleven
profile dimensions remain explicit for VMware, AHV and OpenStack; declarations
are UNASSESSED and AHV discovery remains an explicit collector gap.

## Collector and delivery increment

The independent Inventory worker now consumes fenced HTTP leases and performs
bounded HTTPS GET collection for OpenStack Nova 2.1, Neutron 2.0, Cinder 3.0 and
vCenter `/api/vcenter` VM/network/datastore lists. Destination addresses are pinned
from the independently mounted policy, with certificate-name verification and
redirect rejection. Each stream has its own mounted native credential. Native
responses supply an allowlist of facts; returned links cannot change the target.
Actual product/version/backend coverage remains unqualified.

OpenStack marker pagination continues to an observed empty page, including when
an installation returns fewer than the requested 100 records. VMware lists over
100 objects fail visibly as partial; they are never silently truncated. Missing
creation/incarnation evidence holds matching. AHV remains an explicit gap.

Inventory facts now have a migration-added monotonic delivery sequence, AMQPS
mandatory routing and publisher confirms. A lost confirm or failed receipt commit
replays the original immutable event ID before later facts. The Planning consumer
belongs to P05. The generated PHP operation descriptors, Python campaign client
and TypeScript wire types derive from the new Inventory OpenAPI contract.
Governance adds Inventory as a constrained delegation audience through an additive
migration and preserves recovery rotation checks for its new credential.

The first hosted PostgreSQL/TLS campaign at `8290f144` passed all 70 tests with no
skips (run `37433829615`, artifact `11398072994`). Its original source bindings and
logs are retained in `verification/p04/core-8290f144/`. Later collector, event and
Console work requires its own exact-source runs. The operation and native-input
handoff is in [the runbook](../operations/runbooks/inventory-discovery.md).

## Console increment

The Console now exposes tenant-scoped sites, approved enrollment policies, endpoint
health, discovery commands, eleven-dimensional capability gaps and fixed-generation
observations. Expiry and eligibility holds remain visible. Application matching
checks current Catalogue revision access before recording an unverified proposal.
The client validates generated wire contracts, streams bounded responses and uses
separate workload credentials plus current site-scoped actor delegation. Uncertain
commands retain their original key/body/revision for an unchanged retry. Current
access polling clears revoked views and pauses commands on authority outage.

Local Console checks: 156 passing tests (738 assertions), seven PostgreSQL-specific
checks deferred to hosted qualification; Vue type checking and production build
pass. Governance: 245 passing tests (5663 assertions), twelve PostgreSQL-only checks
deferred to hosted qualification. The new `P04 live discovery, Console and delivery`
campaign requires Chromium, Firefox and WebKit against actual local services,
PostgreSQL TLS, native HTTPS fixtures and an independently observed AMQPS broker.
