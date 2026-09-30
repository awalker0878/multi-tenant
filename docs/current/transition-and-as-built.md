# TRANS-M01 — Transition states and observed acceptance

**Version:** 0.6 · **Status:** Proposed · **Accountable role:** Implementation and operations owners.

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
membership/dependency assertions are persisted; formal owner review, deployed
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
source generations are reported without relabelling history. Formal owner review,
independent enrichment verification, full guided review and B17 closure remain open.
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
creation/evidence editing and independently authorized owner review remain open.

## Engineering and implementation handoff

Bind actual commands/artifacts and results to an accepted MOP; keep secrets and unsanitized evidence outside Git. Supply owner/escalation, monitoring, capacity/support, dependency recovery, measured service RTO/RPO and controlled continuity decisions.

## Acceptance and open work

No observed inventory, completed recovery, signature or activation is prefilled. The responsible owners must accept the exact as-built service scope before operation.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
