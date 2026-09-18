# Bounded Nutanix task-tree readback

**Work package:** I09 known-task observation extension. **State:** candidate native
reader, tested only against scripted local HTTPS until an exact installed-platform
campaign is accepted. This is not a new hosting controller or an activation service.

## Infrastructure responsibility

A platform operation may have a successful parent task while a nested action is
pending, failed or unrelated to the accepted resource scope. The original v4.3
observer intentionally refused all composite tasks. This extension adds a separate,
explicit small-tree profile without changing the meaning of that original profile.

It implements the observation handoff beneath
[separate provisioning authorities](../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md),
[uncertain-outcome discovery](../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)
and [containment precedence](../adr/0032-keep-incident-containment-above-routine-reconciliation.md).
The actual platform owner supplies the recorded IDs and engineering expectations;
this tool never submits, cancels, repairs or rediscovers an operation. A stopped
runner and consistent task data do not establish real writer fencing.

## Native interface and completeness boundary

The profile remains networking/prism **HTTP API v4.3**, based on the official SDK
**v4.3.1** source. Its Task model exposes parent/root references, affected entities,
counts and child references. Importantly, TaskGet returns a **limited child summary**;
the documented listing mechanism for a larger tree is a different operation. [T1–T2]

This reader does not implement that listing/discovery operation. It accepts 2–16
already recorded task IDs, with at most four parent/child levels, and checks that
each native child count and returned list exactly match the explicitly expected
direct children. A partial summary remains UNKNOWN even when the operator knows
additional IDs. There is no assumption that a declared list is complete merely
because every item in that list was fetched. Batch-job summaries and job endpoints
remain unsupported. These size/shape limits are engineering choices, not platform
scale limits or externally mandated thresholds.

| Accepted input | Required native observation |
|---|---|
| Exact root and descendant IDs, operations and parent relationships | Matching Task type/identity/operation, exact parent and root references |
| One creation-time interval for the recorded change | Every task created within that interval, not future-dated |
| Complete declared direct-child sets | Matching integer counts and exact lists; no missing, duplicate or unexpected child |
| Exact affected-resource sets per task | Complete count and ID coverage, within the selected VPC/subnet scope |
| Expected VPC/subnet identity, native tenant and fields | Same existing resource checks and accepted strong ETags |

The root must affect the complete selected resource set; a child has an explicitly
selected subset, including an explicitly empty set where appropriate. All selected
resources must share the accepted native `tenantId`. This does not claim that native
tenancy equals the enterprise Tenant Namespace or WSD. Operations involving other
entities, unobserved permission boundaries or unsupported task shapes remain outside
the profile; do not discard those entities to make the check pass.

## Ordered observation, not an atomic snapshot

Each round reads the declared tree in parent-first order, reads the selected resources,
and rereads the tree in reverse traversal order. This brackets configuration with
progress observations but is not an atomic controller snapshot. The complete task
witness is retained once per round; each resource carries its digest. This avoids
multiplying the entire task tree into every resource record.

The existing observer requires **two identical completed rounds** before reporting
`READBACK_MATCH_NOT_QUALIFIED`. Pending progress does not count toward that completion
requirement. Identity creation time remains stable across rounds, and a terminal task
cannot silently change identity, status or completion metadata. Child creation cannot
predate its parent, and completed child work cannot finish after a parent that is also
reported successful. Unsupported, contradictory or missing metadata keeps the hold.

| Observation | Result and operational consequence |
|---|---|
| Any known child is QUEUED, RUNNING, CANCELING or SUSPENDED | Pending; no replay or implicit cancellation, even at 100% progress |
| Parent succeeds but a descendant FAILED/CANCELED | Partial-failure inspection; existing resources are preserved |
| A failure is seen before a later success response | The prior failure is not erased into a successful sample |
| Missing task, wrong relationship, partial list, batch summary, future time or unknown status | Uncertain; stop rather than broaden discovery or fabricate completion |
| Complete task tree, but resource fields/ETag differ | Configuration divergence; task success does not override it |
| Complete stable task and resource observations | Eligible for the existing **operator recovery review only** |

The policy is conservative when facts conflict: malformed/unknown metadata can yield
an uncertainty hold instead of a specific failure label. It must never become a
permission to proceed. Nonempty success warnings, typed errors or legacy error text
also require review. Their contents are not exported into the report.

## Transport and resource ownership

The implementation reuses the existing exact-origin TLS/GET transport, fixed compiled
path allowlist, private output journal and request/time/body budgets. No response
`href`, redirect, continuation cursor or task-provided URL is followed. Selected IDs
are encoded as individual path segments. Credentials remain environment-injected and
are not part of the manifest or evidence. The original single-task profile remains
unchanged and still refuses composite work.

For T tasks and R selected resources, one successful collection round uses `2T + R`
GETs. The usual three-round setting uses no more than three such collections unless
an earlier stop applies. The existing 400-request and cooperative elapsed-time ceilings
remain effective; a requested larger round count may exhaust those limits and hold.
OS hostname resolution still needs an independent execution deadline. No budget is
raised automatically to finish a tree. Native-role/endpoint acceptance is an external
precondition, not something proved by the supplied engineering-reference strings.

## Evidence and recovery decisions

The same tree-witness validator is applied during online observation and offline
interrupted-change review. It checks every task, relation, selected entity, state and
terminal-history invariant, including completion no later than the recorded sample time, rather than trusting the report's final label or outer
hash alone. A rehashed report with a missing child or inconsistent parent relation is
rejected. Hashes and structural checks are not signatures or authenticity proof:
actual evidence storage and authority remain separately controlled.

Existing incident containment, writer fencing, change generation and quarantine checks
still govern recovery review. The observer and reviewer always retain `may_apply`,
`may_delete` and `may_activate` as false. The tool cannot validate an administrator's
claim that a real writer is fenced or that an effective data path is quarantined.

## Qualification still required

Accept the exact Prism/networking release, returned reference/count semantics,
least-privileged read role, selected operation names and affected entities. Measure
convergence and time consistency on an authorized disposable native scope, including
partial failure and interrupted reads. Preserve known native task IDs; do not infer
them from display names or enumerate a broader tenant to recover an unknown ID.

The local fixtures use synthetic parent/child bodies and operations over real HTTPS.
They are not actual VPC provisioning, complete VM/Flow/storage coverage, native role
proof, task cancellation, controlled repair, backup/restore or operating authorization.
Large/partial trees and batch jobs need a separately reviewed discovery/coverage
profile. The historical I09 backlog remains unchanged; this is a bounded increment.

## Primary interface references

- T1: [Official Prism SDK v4.3.1 task models](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/prism-go-client%2Fv4.3.1/prism-go-client/models/prism/v4/config/config_model.go): Task, TaskReferenceInternal, TaskStatus, affected-entity and child-summary fields.
- T2: [Official Prism SDK v4.3.1 task API](https://raw.githubusercontent.com/nutanix/ntnx-api-golang-clients/prism-go-client%2Fv4.3.1/prism-go-client/api/tasks_api.go): exact v4.3 TaskGet path; separate cancellation and job operations are not invoked.

Reviewed 18 September 2026 for this candidate implementation. No vendor source is
copied into the implementation. Completeness rules, limits and fixture choices above
are explicit local engineering decisions, not new vendor guarantees.

[Execution procedure](../implementation/nutanix-task-tree-readback.md) · [Work record](../../sources/implementation/nutanix_task_tree.json)

## Integration audit against the commissioning baseline

The pending task-tree work was reconciled with main `1d50765345e747d972950a91f839e8adbace3c0f`, retaining the native-reference commissioning kit, its planning CI step and routed-family verification. Navigation regeneration now preserves all three work-package links.

An independent local probe found that offline review originally checked task timestamps against the later review clock, not their own observation timestamp. A rehashed record could therefore describe completion after its alleged observation and still pass consistency review. The corrected reviewer binds each task witness to that round’s recorded observation time. This rejects contradictory chronology; it does not authenticate timestamps or grant authority. Dedicated negative regressions retain the original reproducer.
