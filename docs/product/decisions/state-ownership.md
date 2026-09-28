# Product decision — Assign one authority per state and remove superseded runtime paths

**Status:** Proposed<br>
**Decision class:** New product direction; organizational adoption pending<br>
**Date:** 2026-09-26<br>
**Accountable role:** Product architecture, platform owners and operations; named organizational acceptance is pending<br>
**Scope:** Product control plane, native operations and upgrade; no live target contact is authorized<br>
**Basis:** [ADR-0013](../../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md), [ADR-0016](../../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md), [ADR-0031](../../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md), [ADR-0033](../../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

## Context

Local owner ledgers, journals, Terraform state and native observations protect particular operations. They do not form one distributed multiuser job authority. Recorded approver strings describe external authority but do not authenticate an actor. Compatibility projections, implicit old receipt defaults and runtime imports from repository scripts can preserve a second contract or checkout dependency after a new product path exists.

## Decision

Use one installable application and one current domain contract per object kind. Assign state authority explicitly:

| State | Authority |
| --- | --- |
| Product identities, intent, authenticated approvals, reservations owned by the product, native-operation intent/idempotency and audit metadata | Transactional product database, proposed PostgreSQL |
| Workflow progress, timers and resumption | One selected durable workflow engine; job read models are rebuildable projections |
| Actual resource existence/configuration and native task status | Installed platform and service-owner systems, read back by exact endpoint/native ID/version |
| Declared infrastructure fields | Scoped Terraform state and approved saved plans, subject to the field owner and an explicit handoff before another writer acts |
| IP addresses, names, backup catalogues, CMDB records and other delegated services | Their respective authoritative service owners; the product stores scoped receipts and verification |
| Evidence artifacts | Protected content-addressed evidence store with independently attributable records and retention |

Activities perform native/API side effects using stable operation IDs and idempotency checks. The control plane uses a transactional outbox for workflow submission/signals. Before a retry after an unknown result, reacquire a fenced lease and observe native state; a timeout alone is not permission to repeat a mutation. Containment and incident authority take precedence over routine reconciliation.

Runtime compatibility projections, hidden defaults, fixture fallbacks in executable service mode and old mutation entry points have named migration/deletion gates. Convert retained records offline with counts, digests and native identity reconciliation; drain or fence in-flight work; observe before transferring writer ownership; then remove obsolete readers and dispatch paths. Historical evidence remains readable to an audit viewer without becoming an executable legacy request. Native platform adapters, safety holds and one-time migration code are retained as necessary implementation.

## Alternatives considered

- Keeping the local runner as a second production job authority would split resumption and approval history.
- Treating Terraform state as universal truth would override native and service-owner authority, especially after uncertain tasks.
- A permanent legacy reader or fallback dispatch would let old requests bypass the new canonical checks.

The specific workflow engine and persistence implementation require a technical spike and deployment ADR. This decision fixes ownership and safety invariants, not a vendor selection.

## Consequences and delivery obligations

- Authenticate approvals and revalidate action, actor, tenant/site, plan revision, expiry and revocation at privileged boundaries.
- Persist native task IDs, attempt epochs, held uncertainty and postcondition receipts separately from rebuildable UI status.
- Validate production configuration cannot load demo inventory or qualification; rejected old payloads must fail clearly.
- Scan all runtime callers and serialized contracts before deleting a legacy path; retain immutable history with audited conversion reports.
- Prove restart/replay, duplicate submit, lease theft, lost response and old worker exclusion in integration tests, then native campaigns.

## Acceptance

One mutation owner advances each job/resource after migration. No active caller or retained record requires old runtime semantics, and no unsupported route can return success-shaped output. Actual production acceptance still requires enterprise authority and native evidence.

[Implementation plan](../enterprise-workload-mobility-audit-and-implementation-plan.md)
