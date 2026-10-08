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
tenant concurrency, a 20-job tenant and 1000-job service backlog, a 30-second page lease, three failed
attempts, a one-hour collection deadline, 100 pages and 10,000 observed resources.
Competing tenants rotate per endpoint. Limits are initial engineering bounds;
actual site budgets remain operating inputs. Expired pages cannot refresh a
generation. Native retry continuations contain identifiers, never returned URLs.

## Engineering qualification

The new [P04 workflow](../../.github/workflows/p04-inventory.yml) executes real
PostgreSQL/TLS, immutable-role, competing-tenant, restart, revocation and hostile
page cases and retains logs/source bindings. Local unit checks run in the locked
package. The current local user namespace maps only UID 0; PostgreSQL correctly
rejects that process identity, so the database campaign runs on the unprivileged
hosted runner. This is an environment limitation, not a passing database result.

Worker, Console and published contracts are implemented. Integrated acceptance
is recorded in the final qualification packet. G04 requires actual installed OpenStack/VMware tuple, endpoint,
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

## Final retained engineering evidence

Final qualification source: `6b21490af3a9b0fbd5ce288bfbca8f82c790d6d9`.
Original evidence is committed at `91ee1152ccd723857056aa32cf2217a5d87608fb`.
The [qualification index](../../verification/p04/final/qualification-index.json)
records 75 Inventory and 24 worker tests passing with no skips and three successful
live campaigns of 60 checks/29 commands each. Every engine has zero browser
failures, skips or retries. Each independent broker observer records ten deliveries
for nine original event IDs, with one deliberate replay in order. All 1180
source-revision/path bindings, archive/report/log bytes and source-unchanged checks
were verified. Twenty local checks pass, with their PostgreSQL-only skips explicit.

The [check matrix](../../verification/p04/check-matrix.md) defines the measured
scope, and [corrections](../../verification/p04/corrections.md) preserve failed
attempts and fixes. EV-P04-001–003 record the evidence; BL-P04-001/002 retain the
actual native inputs and receiving reviews. The [G04 assessment](../qualification/gate-reviews/g04-engineering-assessment-2026-10-06.md)
and [completion packet](p04-completion-review.md) explain why P04/G04 cannot be
marked formally complete from these E1/E2 results. No native write or qualification
claim follows from enrollment, profile completeness or the automated campaigns.

The final runtime-source Kubernetes run `37438932585` passed at `fb37bb22`;
product/image/deployment inputs are identical to qualification source `6b21490a`.
The [regression completion receipt](../../verification/p04/final/regression-completion.json)
records that outcome and passing affected P01/P02/P03 regressions, preserving
the original pending receipt separately. No automated campaign remains pending
as P04 engineering qualification work.
