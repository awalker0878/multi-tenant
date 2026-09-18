# Native readback, writer-fencing and reconciliation assurance

**Purpose:** complete the missing assurance layer above the existing NSX, Nutanix and Neutron read-only observers without turning this repository into a native writer, task controller or repair engine.

The existing readers already bind exact resource/task identities, selected expected fields, version tokens and bounded observations. The offline recovery reviewer already refuses blind replay, state-file rollback and automatic activation. I09 remains open because a matching readback does not establish actual writer exclusion, current containment state, complete native applicability or an accountable data-safe reconciliation decision.

## Source obligations

- AUTO-002 requires journaled/idempotent provisioning and activation only on realized current-generation evidence and authorization.
- AUTO-003 requires uncertain outcomes to be discovered and reconciled rather than duplicated.
- STATE-003 requires journaled cross-state/external-service workflow and forbids presenting state-file restoration as infrastructure rollback.
- DRIFT-001 requires security-significant drift to update current technical conformance/readiness until resolved or accepted.
- DRIFT-002 requires emergency changes to be reconciled back into the source of truth.
- DRIFT-003 requires incident containment to outrank ordinary reconciliation until explicit release.
- ADR-0016 requires one authoritative writer per native object/sensitive subresource and actual writer-fencing evidence.
- ADR-0031 requires current native outcome discovery before any data-safe converge or compensation path.

## Existing read-only implementation

The repository already contains:

- `tools/nsx_observe.py` — exact selected NSX Policy/realization readback;
- `tools/nutanix_observe.py` — exact Nutanix networking/task readback;
- `tools/neutron_observe.py` — bounded Neutron exact-resource comparison;
- `tools/recovery_review.py` — offline consistency review of operation, report, fencing/quarantine and generation records;
- the bounded Nutanix task-tree extension for an explicitly enumerated small task graph.

Those tools remain read-only. They do not discover arbitrary inventory, cancel tasks, fence a writer, import Terraform state or perform repair.

## Active assurance index

The active index is `sources/capabilities/native_reconciliation_assurance_index.json` and is intentionally empty.

A future record binds one stable `operation_id` to:

- platform family (`VMWARE_NSX`, `NUTANIX` or `OPENSTACK_NEUTRON`);
- accepted engineering record;
- exact operation scope and resource-set references;
- immutable change record and operation owner;
- exact operation generation;
- review cadence.

## Native interface applicability

Before a readback can support reconciliation, the record must carry current evidence for:

- installed platform tuple;
- exact API/profile version;
- native RBAC for the observer;
- product default/omission semantics;
- authoritative version-token behavior;
- accepted task/entity coverage;
- `coverage_state = EXACT_ACCEPTED_SCOPE`.

This prevents a local fixture profile or documentation snapshot from being reused against a materially different installed target.

## Observation evidence

The observation block records:

- immutable manifest/report references;
- exact SHA-256 digests;
- bounded outcome;
- stable-sample count;
- observation time and validity.

`MATCHED_ACCEPTED_SCOPE` requires at least two stable samples. Pending tasks, partial failure, divergence or unknown results remain distinct outcomes and cannot be promoted to reconciled readiness.

## Writer fencing

A stopped runner, expired lease, Terraform state lock or matching readback is not a writer fence.

Current readiness requires a separate `VERIFIED_FENCED` record containing:

- the actual fencing mechanism;
- exact native scope;
- accountable owner;
- competing-writer review;
- observation and validity interval.

If real fencing is unavailable, the record remains `FENCE_DUE` or `UNCERTAIN`; the repository does not invent a substitute.

## Incident containment

Containment state is recorded separately as `NONE`, `ACTIVE` or `RELEASED` with authority, scope and current-state evidence.

`ACTIVE` always blocks ordinary reconciliation readiness. `RELEASED` requires an explicit release-decision reference. CI never releases containment.

## Reconciliation decision

The reconciliation block binds the same operation generation and records:

- source-of-truth reconciliation evidence;
- data-impact review;
- shared-dependency review;
- accountable decision;
- optional repair/compensation plan;
- decision time.

A completed decision must occur after the native-interface, observation and writer-fence evidence on which it relies.

Supported completed decisions are:

- `RECONCILED_NO_CHANGE`;
- `RECONCILED_ADOPTED_CURRENT_STATE`;
- `RECONCILED_FORWARD_REPAIR_DECIDED`;
- `RECONCILED_COMPENSATION_DECIDED`.

`PENDING_DECISION` carries no completed decision or repair plan and remains held. A forward-repair/compensation decision only describes the accountable next choice; it does not authorize this repository to execute it.

## States

Supported assurance states are:

- `CURRENT_RECONCILED` — current exact-scope observation, verified fencing, no active containment, completed reconciliation and no open gaps;
- `REVIEW_DUE` — operation/gap review expired;
- `OBSERVATION_DUE` — API/applicability or native observation evidence expired;
- `FENCE_DUE` — fencing is unverified, absent or stale;
- `CONTAINMENT_ACTIVE` — current incident containment blocks ordinary reconciliation;
- `RECONCILIATION_REQUIRED` — native outcome is pending/failed/divergent/unknown or decision remains pending;
- `GAPS_OPEN` — current reconciled evidence exists but residual obligations remain open;
- `UNCERTAIN` — authoritative native state cannot yet be reconciled.

## Readiness preflight

`scripts/check_native_reconciliation_readiness.py` compares the exact operation ID, platform, engineering record, resource set and generation with the active assurance record.

A successful result is `NATIVE_RECONCILIATION_CURRENT_NO_MUTATION_AUTHORIZED`.

It does **not** authorize:

- task discovery/listing;
- task cancellation;
- containment release;
- Terraform/native state import;
- forward repair;
- deletion;
- infrastructure apply;
- production activation.

Current repository state remains held because no real native writer-fence/reconciliation record has been supplied:

```sh
python scripts/check_native_reconciliation_readiness.py examples/native_reconciliation_readiness_intent.json.example --as-of 2026-09-18T22:05:00Z --expected-status HOLD_NO_CURRENT_NATIVE_RECONCILIATION
```

Any later repair must use a new current plan/approval and the responsible native owner. Old Terraform state remains a record, not infrastructure rollback.

[Native readback](../NATIVE_READBACK.md) · [Interrupted-change recovery](../INTERRUPTED_CHANGE_RECOVERY.md) · [PROV §5 — Concurrency, ownership and failed execution](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md)
