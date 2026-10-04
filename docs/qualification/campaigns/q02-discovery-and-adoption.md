# Q02 — Discovery and adoption

Q02 verifies R08–R11: commissioned scope, complete observations, collector controls and explicit ownership. It supports P04.01–P04.05, P05 safeguards and P09.03 adoption. G04.01–G04.04 evaluate discovery; G09.03 evaluates native adoption. Read-only discovery never grants mutation authority.

## Scope and ownership

The inventory owner and platform owners provide collector/profile contracts; qualification independently reconciles native results. All VMware, AHV and OpenStack profiles must represent every [capability dimension](../../implementation/requirements-and-qualification.md#3-complete-profile-dimensions-for-all-three-platforms), including unknown and unsupported facts. Initial native discovery covers the selected OpenStack and VMware laboratories; AHV native claims require its own run.

Use E1 for profile/normalization checks, E2 for controlled endpoint faults and E3 for authorized native read-only observation or adoption. An adoption run is separately scoped, authorized and reviewed from the discovery run.

## Preparation

1. Pin installed tuples, API/backend/feature identity, allowed endpoints, resource scope, collector identity and read-only privileges.
2. Seed permitted fixture objects with stable native identities, an inaccessible object, a deleted/recreated identity case and objects belonging to two tenants.
3. Obtain an independently assembled native inventory and privilege-coverage record for comparison. Document what the observer also cannot see.
4. Select generation freshness, paging, endpoint budgets and fair-use limits from approved site inputs.
5. For adoption only, enumerate field/resource owners, old automation writers, proposed ownership transfer, no-change import plan and authorized detach/reconciliation procedures.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q02.01 | Collect all profile dimensions from the selected endpoint | Stable native IDs, source/generation/time and privilege provenance persist; absent facts are unknown | Profile coverage and native comparison report |
| Q02.02 | Drop a page, truncate a result or hide a resource through restricted privileges | Generation remains incomplete or explicitly scoped; counts alone cannot mark it complete | Page trace, coverage declarations and completeness outcome |
| Q02.03 | Delete and recreate an object with a reused name or identifier in a distinct scope | Identity/provenance prevents accidental continuity or ownership transfer | Native history and normalized identity comparison |
| Q02.04 | Interrupt collection, exceed freshness and reconnect with deltas after a gap | Stale facts block dependent eligibility; recovery reconciles a complete generation before clearing the hold | Timeline, generation lineage and assessment hold |
| Q02.05 | Revoke collector credentials; request an unapproved endpoint or foreign-tenant object | Collection stops within the selected revocation behavior; unauthorized endpoint/scope is denied | Enrollment/revocation and access-denial records |
| Q02.06 | Apply rate limits, slow pages and competing tenant collections | Backoff and bounded concurrency respect endpoint budgets; no tenant starvation or uncontrolled retry storm | Request-rate/fairness measurements and queue state |
| Q02.07 | Discover unowned resources and propose a conflicting ownership claim | Objects remain observation-only; collision blocks adoption and native writes | Ownership records, denial and before/after native state |
| Q02.08 | Perform approved no-change import of exact objects/fields with old writer frozen | Import associates existing identities without native change; ownership transfer is explicit and attributable | Approved scope, writer-fence observation and plan/state/native diff |
| Q02.09 | Introduce drift, incomplete state import or an unknown response during adoption | Mutation remains held until reconciled; retry cannot overwrite uncertain or externally owned fields | Fault timeline, state identity and recovery decision |
| Q02.10 | Detach an adopted scope under separate approval and attempt an old worker write | Ownership is relinquished without deleting unmanaged resources; stale authority cannot continue | Detach receipts, stale-writer denial and native comparison |

## Execution and observations

Run Q02.01–Q02.07 before native provisioning consumes discovery. Independently compare the endpoint's permitted object set with collected scope, including hidden privilege boundaries and tombstones. An empty response cannot establish an empty site when access may be incomplete.

Run Q02.08–Q02.10 only for the adoption capability selected in P09. Record the Terraform state identity or equivalent management binding separately from native object identity. A successful import command is not evidence that the plan is no-change or that an old writer lost authority.

Stop adoption when ownership, old-writer fencing or outcome is uncertain. Preserve native resources and state for reconciliation; do not attempt destructive cleanup to make the run appear clean.

## Pass criteria and evidence

Discovery passes only when every required dimension is represented, completeness/freshness is truthful, scope controls hold and the independent observer detects no discovery-induced native changes. Adoption additionally requires exact field/resource transfer, no-change readback and safe collision/drift/detach handling.

Retain profile versions, native tuple, credential-scope references, request/page traces, generation comparisons, endpoint-load observations, independent native snapshots and ownership/state receipts. Separate E2 doubles from E3 platform observations. Register failures and evidence under [the canonical state rules](../../implementation/status-model.md).

## Cleanup and reruns

Remove only test-owned synthetic resources with separate authority; discovery fixtures that pre-existed remain intact. Revoke collector credentials and retain evidence/ownership histories. Repeat affected tests after platform/API privilege changes, identity normalization, paging, freshness, ownership transfer or adapter upgrades.
