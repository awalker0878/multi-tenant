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
