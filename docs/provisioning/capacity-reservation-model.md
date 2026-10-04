# Capacity reservation model

Reviewed capacity arithmetic is not a reservation. The portable package can compute
exactly what a WSD demands and exactly what a reviewed cluster has left, but capacity
is **held** by an authoritative reservation owner outside this repository. A plan that
treated its own arithmetic as a held reservation would let a downstream owner build on
capacity nobody reserved.

This document describes the seam that hands a reviewed reservation **intent** to that
authoritative owner and reads the owner's own answer back. The module is
`provisioner/allocations/owner.py`; the preserved preflight arithmetic is
`provisioner/allocations/reservations.py`. No code here contacts an owner, writes a
record or grants capacity.

## What is preserved, and what is added

| Layer | Module | Says |
| --- | --- | --- |
| Preflight arithmetic | `provisioner/allocations/reservations.py` | what the reviewed inventory leaves, and that the proposal is disjoint |
| Owner seam | `provisioner/allocations/owner.py` | the intent to hand over, and the owner's own answer read back |

The preflight is unchanged and stays `applied: False`. The owner seam adds the
portable documents the owner needs, and nothing else.

## The documents

| Format | Producer | Binds |
| --- | --- | --- |
| `hosting-capacity-view/1` | `capacity_view(plan)` | the commissioned capacity snapshot: inventory digest/status/authority, site, platform and every reviewed zone with its demand, committed-after position and remaining units |
| `hosting-capacity-binding/1` | `binding(plan, ...)` | the reservation identity: `reservation_id`, `operation_id`, `generation`, `plan_digest`, `view_digest`, the five delivery scope keys and the envelope |
| `hosting-capacity-request/1` | `request(plan, ...)` | the exact request `provisioner/allocations/capacity_owner.py` already validates: format, owner, reservation and operation identity, generation, scope, pool, units, capabilities |
| `hosting-capacity-owner-handoff/1` | `handoff(plan, ...)` | the whole proposal: binding, view, request, per-zone rows, the facts the operator must supply, the limits and a content digest |
| `hosting-capacity-owner-facts/1` | the operator | the recorded owner facts the repository cannot review: owner id, pool id, capabilities, database path, envelope id and envelope record digest |
| `hosting-capacity-reconciliation/1` | `reconcile(...)` | what the exported reservation records actually say about this identity |

The view deliberately carries **no generation**. Two generations of one WSD read the
same commissioned capacity, so a generation in the view would make an unchanged
inventory look changed. The generation that claimed the capacity is in the binding,
where it belongs.

## The compiled request is the owner's own contract

`request()` emits a document that `tools/capacity.validate_request` accepts unchanged:
the exact nine keys, the exact five scope keys, `units` over exactly
`{vcpu, memory_mb, storage_gb}` with a non-zero unit and a bound of `10 ** 15`, and a
non-empty duplicate-free capability list. `validate_request()` in this module mirrors
that contract so a malformed intent is refused here rather than by the owner.

Units are the reviewed arithmetic converted to the owner's units, rounded **up** so the
owner is never undercharged: `memory_mb = ceil(gib * 1024 ** 3 / 10 ** 6)` and
`storage_gb = ceil(gib * 1024 ** 3 / 10 ** 9)`. Rounding is per zone, because the
owner reserves per cluster; recorded headroom is rounded **down** instead, so a
refusal is never lost to a rounding artifact.

## Reconciliation states

`reconcile(identity, index, as_of=...)` validates the repository's exported
reservation evidence with the repository's existing checker
(`provisioner/allocations/reservation_evidence.py`, reached only through
`provisioner/repository.py`) and classifies the proposal. A missing record is a
proposal, **never** a confirmation.

| State | Meaning |
| --- | --- |
| `HOLD_ENVELOPE_NOT_BOUND` | no envelope digest was recorded, so the owner was never asked |
| `PROPOSED_NOT_CONFIRMED` | the envelope is bound and the owner holds no record for this identity |
| `CONFIRMED_BY_OWNER` | the owner holds a live record for this exact identity and envelope |
| `HOLD_RESERVATION_IDENTITY_OR_INTENT_CONFLICT` | the owner holds a record for another operation or generation, or for another envelope |
| `HOLD_DISCOVER_RESERVATION_OUTCOME` | the record or one of its dependency handoffs is `UNCERTAIN` |
| `HOLD_TERMINAL_RESERVATION_NEW_OPERATION_REQUIRED` | the owner's record is `RELEASED` or `EXPIRED` |
| `EXISTING_CONSUMED_RESERVATION` | the owner's record is `CONSUMED` |

The four refusal states deliberately borrow the refusal vocabulary of the preserved
preflight (`provisioner/allocations/reservation_preflight.py`) so an operator reads one
vocabulary. `require_settled`, `require_confirmed` and `require_current` refuse with
`CAPACITY_RESERVATION_CONFLICT` (a definite no), `CAPACITY_RESERVATION_UNRESOLVED` (the
owner has not answered yet) or `CAPACITY_RESERVATION_UNCONFIRMED` (the answer is not a
confirmation).

## Authority

`CONFIRMED_BY_OWNER` is the only state where `confirmed` and `may_allocate` are true,
and it is reachable only from a live record the authoritative owner exported. Every
state reports `may_apply: false` and `may_activate: false`: a reservation is capacity,
never change authority. `reconcile` is a reading — it creates, confirms and releases
nothing.

The `capacity-proposal` conformance check is repository-side: it reports the reviewed
arithmetic as a proposal, naming `REPOSITORY_CAPACITY_ARITHMETIC` as its authority and
`capacity-confirmation` as the check that settles it. The `capacity-confirmation` check
is `EXTERNAL`: it is `PENDING_EXTERNAL_EVIDENCE` until the owner answers, `PASS` only on
`CONFIRMED_BY_OWNER`, and `FAIL` on a definite refusal. The `capacity` evidence record is
bound to the view digest and reports the owner's state, so an approval never has to guess
whether capacity is held.

A reading is only evidence for the plan it names. A reconciled capacity reading whose
operation identity, generation, plan digest or view digest is not this plan's stays
`PENDING_EXTERNAL_EVIDENCE` and reports the mismatched keys, so another generation's
confirmation is never read as this one's and a stale reading never becomes a pass.

## Concurrency

`require_exclusive(reservations)` groups recorded rows by
`(pool_id, view_digest, cluster)`, skips rows this operation already owns and refuses
with `CAPACITY_RESERVATION_CONFLICT` when the combined demand exceeds the recorded
available units. Two concurrent operations that both read the same stale snapshot
therefore cannot both be satisfied from it, and a lost response is never retried into
a duplicate reservation: the identity is derived from the reviewed plan, so the second
attempt reconciles the first owner's record instead of creating a second one.

## What this does not claim

No document here asserts that a reservation exists, that an owner was contacted or
that capacity was granted. Every plan stays `PLANNED_DISABLED_NOT_AUTHORIZED` with
`native_contact: false`; the repository compiles an intent, reads exported evidence
and refuses. The authoritative reservation system, the envelope record and the
database are external, and this repository holds no credential for any of them.