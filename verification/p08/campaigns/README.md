# P08 migration campaign qualification

The [verified index](qualification-index.json) retains original hosted archives,
source bindings, logs and results. Run `python scripts/p08/verify_campaign_retained.py`
with the recorded Git objects present. Earlier P08 evidence remains unchanged.

Source `5e2b4a62f2c940bbdb06432c8922d43301e3482c` passes all 35 component commands
and 811 tests without skips: Inventory 96, Planning 119, Lifecycle 330,
Lifecycle-worker 204 and Inventory-worker 62. All three actual Vue/Inertia migration
journeys pass five browser quality commands without skips, retries or flaky results.
The independent Console package passes 23 commands, including Pint, Larastan,
Deptrac, TypeScript and build. Pest records 192 passes, 911 assertions and seven
explicit separate-broker-campaign skips; those skips are not counted as passes.
All 14 workflows triggered at that source completed successfully, including
identity, planning, execution/replay, native readiness, contracts, images, Compose
and Kubernetes. Their exact run identities are in the [regression receipt](regression-status.json).

The verifier checks 701 component, 226 browser and 302 Console source bindings,
the original archive digests, every reported command log and browser artifact,
JUnit counts and the Console test summary. The [campaign screenshot](migration-campaign.png)
is copied unchanged from the final archive and visually inspected. Its hostile
campaign name is synthetic test data rendered as literal text.

| Surface | Verified behavior | Boundary |
| --- | --- | --- |
| Durable scheduling | Atomic native admission/member assignment; dependencies, stagger, windows, blackouts, outage groups and fair consideration of blocked members | Real PostgreSQL with synthetic owner and native peers |
| Performance and outage | Measurements required for each used phase and concurrency; stale/unsafe observations hold; conservative estimates and approved outage objective enforced | No physical route was benchmarked |
| Shared resources | Cross-campaign/tenant allocation accounting, current capacity checks, retained uncertain reservations and separately observed cleanup | Actual native publishers and stable physical pool identities require commissioning |
| Current authority | Scoped Console delegation, immutable owner-resolved plans, observer-specific publication credentials, revision and replay checks | No native account or writer was commissioned |
| Console | Create/list/read, scheduling, pause/resume, queued cancellation, uncertain-request recovery, revocation and safe rendering | Actual Vue/Inertia browser with isolated HTTP fixtures |

## Original failure and correction

Run `37650245430` at `9c1adaa3ade546b4f187420ee588204f128387e1` passed its
797 component tests but failed the Lifecycle Ruff format check. The original
archive, 687 source bindings and failed command `14.log` remain retained.
Commit `f29325f6b97c4118a3db80ca077d2659d921a388` applies only the required test
formatting. Later API and Console increments culminate in the final passing source
above. No validation or quality rule was weakened.

## Remaining native work

These are E2 software results. Campaigns accept complete approved native plans;
the current Planning preparation does not yet produce those plans. Real account
commissioning, owner/runtime composition, benchmark producers, copied-guest/data/
service/fencing/traffic/recovery adapters, qualified converter rootfs and reconciled
long-transfer continuation remain open. Native Q05/Q06/Q07 and G07/G08 receiving
have not been supplied. No migration dates, throughput numbers, account permissions,
VM migration or phase completion are inferred from these tests.

The [operations record](../../../docs/implementation/p08-operations.md) describes
implemented controls. The [completion packet](../../../docs/implementation/p08-completion-review.md)
records the actual source/target references, worker placement and application-owner
protocols needed to bind the remaining work. Development authorization remains in
effect; this evidence does not request it again.
