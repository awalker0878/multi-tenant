# TRANS-M01 — Transition states and observed acceptance

**Version:** 0.11 · **Status:** Proposed · **Accountable role:** Implementation and operations owners.

## Scope and authority

Migration, recovery, retained-state conversion and as-built acceptance across explicit intermediate states; observations and accepting authority remain external.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [OPS §3](../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md) · [OPS §6](../operations/recovery-transition/6-migrate-and-fail-back-without-conflicting-writers.md) · [QUAL §7](../assurance/site-qualification/7-operating-accountability-handover-and-change.md).

## Design content

Record observed current ownership and topology before introducing an isolated target. Separate target construction, authorized data transfer, preproduction validation, final consistency/writer fencing, controlled exposure, stabilization and old-service retirement. Each intermediate state has explicit routes, identities and protected dependencies, not just a before/after diagram.

A lost native response may leave running work. Retain request/plan/state-generation identity and recorded task IDs; discover actual results before another operation. A stopped runner is not confirmed fencing. Do not override incident containment to restore ordinary desired state.

After target writes, failback requires an assessed reverse-consistency process; restarting the old source is not a universal rollback. Retire obsolete live paths and credentials while retaining held data, usable keys and accountable copies. Record the evidence for sanitization rather than infer it from an object disappearing.

The as-built record compares intended and actual resources, interfaces, versions and ownership. Explain every deviation, test its effect and record open risks or conditions. Distinguish a code test, native qualification, initial operating readiness and formal authorization.

### Application migration transitions

A reviewed plan separates source inventory/adoption, isolated target provisioning,
initial transfer, rehearsal, source quiesce/fencing, final synchronization, traffic
switch, target write admission, stabilization and source retirement. Each transition
binds the immutable plan, exact dataset/member set, authority, native IDs, expected
postconditions and a safe hold/recovery decision. The complete graph is still an
implementation deliverable; these phases do not describe an already accepted run.

Keep data integrity and metadata expectations per dataset, complete consistency-group
joins and independent source/target observations. An interruption after an external
effect must reconcile the actual native task and resource before another attempt.
In-flight or uncertain writers are not cleared because a worker lease, SSH session
or workflow task expired. Source shutdown and source-writer exclusion are distinct.

Before target writes, rollback may restore the original serving path only when the
approved strategy and observations allow it. After target writes, use the explicitly
qualified reverse-sync, restore or repair procedure. Record the divergence interval,
accepted loss limits, fencing and measured recovery result; do not present stale
source restart as generic failback.

### Revision and retained-state conversion

The expanded profile requirements change catalogue revisions and derived plan
digests. Preserve old signed plans/receipts as immutable history. Reassess open work
under the new catalogue and obtain new approvals; do not reinterpret old signatures
under new requirements or silently replace their source receipts.

The capability and native-qualification owners were moved into the installed package
and their former script entry points removed without wrappers. The retirement
register guards against reintroduction. This does not remove other runners with
retained state: inventory their files and native operations, freeze new writes,
drain or hold in-flight work, reconcile independently, convert exact old schemas
in an offline importer and verify counts/identities before enabling one replacement
writer. Conversion failure preserves the hold and original evidence.

### Current as-built and release record

The repository's engineering profiles have no selected installed tuples or native-
qualified claims. The admitted Temporal job is an authority gate, not a completed
provisioning/migration run. Discovery has signed publication/comparison components;
the installed collector now composes native reads, signing and publication. Draft
membership/dependency assertions and signed assessment-only owner decisions are
persisted separately; owner-facing signing and application-wide planning, deployed
credential custody and scheduling remain open. Lower-level provisioning and transfer contracts do not close the missing
orchestration, fencing, cutover and post-write recovery paths.

Record B01–B50 implementation, automated verification, native qualification and
operating acceptance separately in the [execution plan](../product/enterprise-workload-mobility-execution-plan.md).
Required release evidence includes actual restore/HA/DR, security and failure tests,
measured performance, incident ownership, a controlled pilot and accepted directed
routes. No site or production workload was changed by this repository revision.

### Research increment and unchanged execution acceptance

This increment changes profile, policy and observation interpretation; rebuild
planning fixtures and re-review new plan/snapshot digests rather than relabeling
old evidence. Local tests cover typed requirements, unknowns, source preservation,
native attribute parsing and destination isolation. Native feature realization,
complete admitted workflows, fencing, final synchronization and cutover remain
separate implementation and qualification obligations.
Retain the pre-target-write versus post-write recovery boundary. Once target data
has changed, returning to the retained source needs an independently reviewed
reverse-sync/restore/repair decision. A failed target check does not authorize
source restart, key disposal, old-writer activation or target deletion.

See [verified research decisions](../engineering/platform-migration-research.md) and
[existing wave-plan delta](../product/enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta).

### Persisted application drafts and attributed assertions

The control API now stores immutable, revisioned application proposals pinned to
an exact observed discovery generation. Selected members must be observed VMs;
partial inventory may support a draft but never an accepted or complete application.
The authenticated author and database time are separate from asserted owner IDs,
dependency sources and consistency groups. Unresolved dependencies remain visible.
Saving a draft creates no owner review, adoption, capability claim or execution grant.

The [application-draft contract](../engineering/application-drafts.md) defines the
actual package owners, scoped PUT/GET routes, expected-revision conflict checks,
original retry semantics, SQL migration and deployment grants. Source-generation
publication and draft creation share their cooperative lock; authority is rechecked
after waits and before commit. Exact retries retain original author/time; later
source generations are reported without relabelling history. The separate signed
owner-review path below evaluates exact-draft assessment decisions. Independent
enrichment verification, owner-facing workflow integration and B17 closure remain open.
The [operator continuation](../engineering/application-draft-operator.md) now supplies
bounded latest-draft listing and CLI save/load/history through the existing API.
Explicit source/revision pins and matching content acknowledgements prevent silent
rebase or success claims after an ambiguous PUT. Listing is a live page, not an
immutable export. Neither commands nor summaries accept ownership or migration.

### Bounded browser draft workspace

The [browser workspace](../engineering/application-draft-browser.md) now lists and
loads existing unreviewed drafts and edits name, proposed owner and startup order.
It retains the exact source/revision and every read-only membership, dataset and
dependency assertion. Historical/superseded records cannot be edited. Explicit save
confirmation, exact content acknowledgements and GET-only uncertain-save
reconciliation use the existing API; no browser action accepts ownership or launches
migration. Tab identity changes clear state and suppress late replies. Full browser
creation/evidence editing and owner-facing signing/review presentation remain open.
Independently signed review evaluation is provided by the separate service below.

### Independently signed application-owner decisions

The existing signed assessment store now accepts exact-draft `APPLICATION_REVIEW`
decisions from independently enrolled `APPLICATION_OWNER` subjects. Owner identity
must match the proposal and differ from its editor. Acceptance/revocation is bound
to the complete saved draft, inventory generation and proposal digest. Live trust,
revocation and scope are rechecked; newer drafts or inventory cannot inherit an old
review. No draft status, native ownership or execution approval is rewritten.

The scoped read-only review endpoint composes retained proof with the existing
application-candidate validator. Incomplete/stale inventory remains held and unknown
dependencies stay explicit; external dependency evidence remains unverified.
Migration 0022 and narrowly scoped ingest-role SELECT rights are required. See the
[signed owner-review contract](../engineering/application-owner-review.md) for
fields, locking, API states, deployment, tests and remaining application-wide
planning and owner-facing workflow integration.

### Operator inspection of signed owner review

The existing thin CLI now reads an exact draft's current signed owner-review status,
optionally checking its retained record digest. It preserves source/evidence/time
references and rejects contradictory status or authority claims without issuing
signatures, changing drafts or launching migration. A successful read of a hold or
revocation does not make it acceptance. The
[review command contract](../engineering/application-owner-review.md#inspect-the-review-from-the-operator-cli)
records exact request/response, tests and remaining signing/browser/application-wide
planning work. No new database migration, privileges or execution authority are added.

### Reviewed application comparison

The [application comparison contract](../engineering/application-comparison.md)
connects exact retained application drafts and independent owner decisions to the
existing per-member destination engine. Every member and guest profile is checked;
combined VM-slot, CPU, memory and logical-disk demand is checked against one selected
capacity identity. Missing facts, source changes, evidence revocation and unresolved
dependencies cannot disappear behind eligible member rows. No capacity is reserved,
no application-wide data/policy outcome is qualified, and no native work is admitted.

Inputs are immutable and current authority/evidence is rechecked, not represented
as an atomic estate snapshot. Results retain all members and exact source/review
bindings. B17/B19/B20 progress does not close Wave 2: independent visibility,
remaining native facts, verified external dependencies and B22 scheduling/scale
still precede wave closure. Wave 3 reserve/apply owners remain separate work.

## Engineering and implementation handoff

Bind actual commands/artifacts and results to an accepted MOP; keep secrets and unsanitized evidence outside Git. Supply owner/escalation, monitoring, capacity/support, dependency recovery, measured service RTO/RPO and controlled continuity decisions.

## Acceptance and open work

No observed inventory, completed recovery, signature or activation is prefilled. The responsible owners must accept the exact as-built service scope before operation.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)

### Application-comparison operator and response identity

The [installed application-comparison command](../engineering/application-comparison-operator.md)
now consumes the reviewed application service through the existing remote API
transport. Report format 2 binds the exact canonical selection, including all
member profiles, source/draft references, destination pools and method/network/data
modes. The client rejects old/mismatched reports, missing members and contradictory
capacity/status claims; it neither supplies owner authority nor calls native owners.
Single-VM comparison and signed review formats remain unchanged. This is B19/B20
operator access, not B23 reservations, B24 provisioning or closure of Wave 2.
The [saved-application browser](../engineering/application-comparison-browser.md)
now consumes the same format-2 service. Only an unchanged current draft supplies
membership; all guest profiles and destination selections remain explicit. Reports
retain every member, exact source/review/pool bindings, capacity gaps and held owner
decisions. Changes to drafts, destinations, route settings or tab identity invalidate
earlier advice and suppress late responses. The component shares the existing portal
identity and destination picker; it neither creates approval nor reserves resources.
Guided draft creation/evidence editing, visibility/dependency evidence and B22
obligations remain open; no production acceptance is recorded here.
