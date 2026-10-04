# Q03 — Planning and authority

Q03 verifies R12–R17, with required tenant, network and sovereignty inputs from R04/R07/R32. It supports P05.01–P05.06 and P06.01/P06.03. G05.01–G05.04 evaluate assessment and planning; G06.01/G06.02 evaluate admission. Native outcomes remain the responsibility of the applicable later campaign.

## Scope and ownership

Planning owns assessments and immutable plans, governance owns approvals, lifecycle owns admission and reservation journals, and assurance owns qualification decisions. The architecture/quality leads review cross-context invariants. E1 verifies deterministic compilation; E2 verifies service integration, races and failure behavior.

Use the [planning](../../services/planning.md), [governance](../../services/governance.md) and [lifecycle](../../services/lifecycle.md) specifications. Test operational admission separately from the explicitly authorized isolated laboratory campaign lane.

## Preparation

1. Seed one complete application intent and two authorized destinations with different capability, capacity, service and topology facts.
2. Prepare fresh, stale, incomplete and conflicting observations; current, expired, revoked and absent qualification records; and unsupported mandatory requirements.
3. Establish fixture policy, sovereignty, tenant/domain, guest and recovery requirements; record exact profile/contract versions.
4. Provide controlled capacity/IPAM/snapshot/staging owner APIs with idempotent receipts, partial failures and independent observation.
5. Prepare distinct requester/approver identities, bounded lab authority, approval expiries and mutable grants for revocation tests.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q03.01 | Assess both destinations against the same pinned intent | Requirement-level eligible, blocked or unknown findings explain facts, qualification, limits and remediation | Input digest set and comparison findings |
| Q03.02 | Remove a mandatory capability, freshness fact, sovereignty constraint or exact-tuple qualification | Operational eligibility is blocked or unknown; no silent downgrade, vendor-wide or reverse-route inference | Negative requirement matrix and admission result |
| Q03.03 | Compile identical inputs twice, then alter one material input | Canonical plan identity is stable for identical scope; changed input creates a different reviewable plan/digest | Plan canonicalization/diff report |
| Q03.04 | Inspect the compiled graph, mappings, budgets and recovery boundaries | Every effect has owner/scope, ordered preconditions, pinned artifacts and declared uncertain-outcome treatment | Plan completeness and ownership review |
| Q03.05 | Reuse approval after changing plan/action/resource/expiry; revoke the approver grant before admission | No changed or stale authority admits work; clear hold/denial is audited | Approval-binding and revocation timeline |
| Q03.06 | Race two plans for the same bounded capacity/address scope | Lifecycle journal and authoritative owner receipts prevent double allocation; loser has a deterministic hold | Race history and independent allocation readback |
| Q03.07 | Succeed at one reservation owner and fail or lose the reply at another | Partial state remains explicit; reconciliation precedes compensation or redispatch | Journal, receipt identities and fault timeline |
| Q03.08 | Expire a reservation while a live resource may consume it; retry release/renew/confirm | Timer alone cannot release live allocation; retries are idempotent and resolved through owner observations | Allocation lifecycle and native-double readback |
| Q03.09 | Submit a laboratory plan to operational admission or widen approved lab endpoints/credentials | Authority lanes remain distinct; bounded campaign scope cannot authorize production or extra resources | Lane/scope denial matrix |
| Q03.10 | Change observations or qualification after the operator opens the comparison/approval screen | Stale UI cannot approve/admit changed scope; user receives precise differences and a new review path | Browser/API concurrency report |

## Execution and observations

Capture assessment inputs independently from displayed findings so a reviewer can reproduce each outcome. Distinguish technical feasibility from operational eligibility: an unqualified candidate can be assessed for an isolated campaign without becoming eligible for normal execution.

Treat reservations as coordinated owner operations, not a claimed global transaction. Observe the lifecycle journal and each authoritative owner before deciding whether a partial reservation is held, confirmed, compensated or safely released.

Interrupt cases at the pre-admission and immediately-before-effect boundaries. Passing one initial authorization check does not establish authority for a later effect after grants, observations or qualification changed.

## Pass criteria and evidence

Every selected mandatory requirement must have an explainable disposition. No unsupported or unknown mandatory control may produce operational eligibility; no material plan change may retain its old approval. Reservation uncertainty must preserve the affected budget until observation resolves it.

Store canonical plan bytes/digests, input revisions, findings, approval/admission history, owner receipts, concurrent timelines and UI observations. Bind actual evidence to G05/G06 criteria in the [delivery register](../../implementation/delivery-register.yaml); follow the [evidence rules](../../implementation/status-model.md).

## Cleanup and reruns

Reconcile and release only confirmed unused fixture reservations; preserve unresolved allocations for the recovery procedure. Revoke synthetic grants and campaign authority. Rerun affected cases after capability rules, canonicalization, approval/admission, profile freshness or allocation-owner contract changes.
