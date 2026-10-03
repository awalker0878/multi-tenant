# TRANS-M01 — Transition states and observed acceptance

**Version:** 0.19 · **Status:** Proposed · **Accountable role:** Implementation and operations owners.

## Scope and authority

Migration, recovery, retained-state conversion and as-built acceptance across explicit intermediate states; observations and accepting authority remain external.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [OPS §3](../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md) · [OPS §6](../operations/recovery-transition/6-migrate-and-fail-back-without-conflicting-writers.md) · [QUAL §7](../assurance/site-qualification/7-operating-accountability-handover-and-change.md).

## Design content

Record observed ownership/topology before introducing an isolated target. Every
intermediate state names routes, identities, protected dependencies, data consistency,
authorized writer and observer. A before/after diagram or native task acknowledgement
cannot prove quarantine, useful-service readiness or absence of another writer.

### Provisioning and migration states

Separate target preparation, saved-plan approval, native realization/readback, guest
readiness, authorized transfer, isolated rehearsal, source quiesce/fencing, final sync,
controlled exposure, stabilization and retained-source retirement. Recheck current
approval, epoch, grant and qualification immediately before each effect. Retain exact
plan/state/task identities across interruption; discover accepted work before retry.
A stopped runner or power-off request is not independent fencing. Incident containment
must not be overridden by ordinary reconciliation.

Before target writes, returning to the source still needs verified consistency and
writer exclusion. After target writes, recovery requires assessed reverse-sync,
restore or forward repair; restarting the old source is not a universal rollback.
Activation does not authorize disposal. Retain accountable copies and usable keys
until observation-backed cleanup, sanitization and capacity/address release decisions.

### Discovery and operator restart behavior

Installed native reads, original signing/custody and explicit publication are composed.
A repeated authorized stage resumes retained bytes. Shared-outbox capture claims exclude
cooperating first writers; interrupted intents remain held, not silently recollected.
These controls do not provide global scheduling or restart-proof enterprise authority.
Batch stop drains bounded active work and leaves any staged result discoverable; it
cannot assert rollback or that no read occurred. Process-local rate counters are not
durable fleet budgets or DR high-water marks.

Draft retries retain original author/time/content and exact source revision. Signed
owner decisions do not convert proposals into mutation rights. CLI/browser comparison
report 2 retains all member/profile/source/review/destination pins. Draft, route,
destination or identity changes invalidate advice; late replies are ignored. The
installed offline owner signer prepares and signs exact-draft assessment decisions;
authenticated artifact delivery and actual owner/key onboarding remain open. The
[exact-draft browser review](../engineering/application-review-browser.md) now displays
all existing review states without signing or changing immutable draft status. It
clears stale advice and preserves uncertain draft saves when the tab becomes hidden.
Reported supersession requires explicit reload, never source rebasing or review reuse.
Application-wide migration planning and operating acceptance remain open.

Freshness inspection/history are implemented, including on-demand exact-ID checks,
predecessor/cursor integrity, migration 0023, narrow grants and atomic audit. A finite
periodic evaluator reuses deterministic target/time-slot IDs after restart and projects
digest-bound alert intents without sending notifications or collecting inventory. Restore
must reconcile generation history, audit and authority before accepting new writes.
Deployed service scheduling, alert delivery/acknowledgement, periodic collection and
fleet-wide recovery remain open.

### Collector and catalog transition

Earlier OpenStack selectors are retired, not redirected. Enroll selector 3 with new matching
campaign/witness/credential material, capture a fresh signed generation and reassess
raw/normalized identities. Preserve old signed evidence without relabelling. CPU/memory
and image/volume/attachment facts now survive collection, but nominal flavor storage
and a guest device label do not establish complete disks, boot order or path authority.

Availability catalog 18 corrects security-zone wording and changes digest-bound
resolution/plan/example identities. Typed requirements and cross-profile checks reject
malformed values, insufficient workload counts and unsupported independent-site
recovery before placement. Previously approved plans must be regenerated and reviewed;
do not reinterpret them under new code. OZ/RZ/PAZ names do not prove physical HA.
No active source or native state was migrated by this documentation/code change.

### Retained-state conversion and as-built evidence

B05/B48 require actual retained-record inventory, immutable originals, exact native-ID,
count/digest reconciliation and observation-only import. Freeze/drain old writers,
assign one owner, independently verify exclusion, migrate consumers, then delete
superseded paths. No compatibility wrapper preserves competing execution authority.
An as-built record compares intent and observation for resources, interfaces, versions,
ownership and qualified operations; explain deviations and untested conditions.
No observed inventory, signature, restore, activation or receiving-owner acceptance is
prefilled from examples. Bind code/artifact revision, installed tuple, campaign, scope,
result and limitations separately for implementation, tests, native qualification and
operational acceptance. The gate-only admitted workflow and uncomposed native/transfer/
cutover/recovery paths remain explicit B01–B50 work, not accepted service operation.

### Signed owner artifact intake

Custodian intake now uses the existing signed-evidence writer and create-only local
receipts. A commit acknowledgement loss stays unknown; receipt failure after a confirmed
commit retains recorded=true. Preserve artifacts and reconcile the exact evidence;
neither case authorizes deletion, a replacement signature or an automatic retry.
An expired decision may remain unretryable despite historical ingestion. The receipt
never refreshes owner validity or replaces a newly evaluated server review.

See the [custodian intake contract](../engineering/application-review-intake.md).


The Terraform catalog implementation is now package-owned at
`provisioner.execution.terraform_catalog`; every in-tree consumer migrated and the
old tools module is removed without an alias. The reader validates finite JSON,
canonical source paths, local root/module ownership and the registered source set.
Existing catalog/configuration/plan bytes remain unchanged. Clean build staging
removes deleted Python owners and bytecode; source-overlapping output is refused.
Installed tests load the reader from bundled resources with legacy imports blocked.
This does not convert state, renew old source-bound approvals or close other B05
runtime owners. See the [catalog runtime contract](../engineering/terraform-catalog-runtime.md).

### Checkpointed collection restart

An opted-in batch saves a start before calling the existing collector. Process loss
or unconfirmed completion leaves an unknown task; another schedule invocation cannot
silently recollect it. Reconciliation consumes only the original signed outbox object
and appends a transition instead of rewriting history. Completed tasks are historical
records and do not refresh inventory. The private journal must be restored together
with its manifest/configuration and original outbox custody; missing or divergent
history holds further local scheduling. A restored consistent prefix still needs
independent high-water-mark reconciliation; this implementation is not a fleet-wide
disaster-recovery authority.

See the [checkpointed scheduling contract](../engineering/discovery-checkpointed-scheduling.md).

### Reservation-evidence reader transition

The exported reservation reader moved into package ownership with all consumers and
commands migrated. The old script and cached bytecode are excluded from fresh builds.
Existing record/index formats, canonical digests, uncertainty handling and owner scope
are unchanged. This is not a retained-state importer or an in-place installation
upgrade. Invalid aliased/linked references require owner-controlled correction, never
silent relabelling of retained evidence. See the
[runtime contract](../engineering/reservation-evidence-runtime.md).

## Engineering and implementation handoff

Bind actual commands/artifacts and results to an accepted MOP; keep secrets and unsanitized evidence outside Git. Supply owner/escalation, monitoring, capacity/support, dependency recovery, measured service RTO/RPO and controlled continuity decisions.

Detailed producer/consumer, response, retry and deployment contracts remain at:

- [verified research decisions](../engineering/platform-migration-research.md)
- [application-draft contract](../engineering/application-drafts.md)
- [operator continuation](../engineering/application-draft-operator.md)
- [browser workspace](../engineering/application-draft-browser.md)
- [signed owner-review contract](../engineering/application-owner-review.md)
- [application comparison contract](../engineering/application-comparison.md)
- [installed application-comparison command](../engineering/application-comparison-operator.md)
- [saved-application browser](../engineering/application-comparison-browser.md)
- [batch staging path](../engineering/discovery-batch-scheduling.md)

See [the current research review](../engineering/platform-capability-review-2026-10-01.md) and
[the B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md).

## Acceptance and open work

No observed inventory, completed recovery, signature or activation is prefilled. The responsible owners must accept the exact as-built service scope before operation.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
