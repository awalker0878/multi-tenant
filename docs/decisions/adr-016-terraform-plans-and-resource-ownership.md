# ADR-016 — Terraform plans and resource ownership

Owner role: Infrastructure lead. Related phases: P00, P05, P06, P07. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Infrastructure execution must apply the reviewed resource change and prevent overlapping ownership between Terraform, direct provider APIs and other tools. The proposed baseline uses reviewed saved plans with explicit resource/field ownership. Tool versions, backend, workspace structure and lock behavior remain unresolved.

## Decision and scope

Reviewed Terraform saved plan and explicit resource/field ownership; tool/backend versions unresolved.

Initial checkpoint: LATER: assign owner in P00; select before P05.04 plan model.

Refinement and validation: Lock backend/workspace/ownership and toolchain before P06.03/P07.02; qualify uncertainty/recovery at G07.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Saved plan bound to approved intent and ownership | Supports review of a concrete change while requiring artifact integrity, state binding and freshness checks. |
| Re-plan automatically at apply time | May adapt to drift but can change the approved effect; a changed plan must return through approval. |
| Direct API ownership for all resources | Avoids Terraform state for those resources but transfers planning, locking, reconciliation and recovery responsibilities to adapters. |

## Consequences

- An ownership map identifies the sole writer for every managed resource or field and handles externally owned resources explicitly.
- State, plans and credentials require protected storage; uncertain apply outcomes require reconciliation before retry.

## Unresolved details and evidence needed

- Select tool/provider versions, backend/workspace boundaries, locking and state recovery ownership.
- Define plan digests, approval binding, expiry, drift invalidation and adoption/import behavior.

## Acceptance and validation

- Finalize the immutable plan model before P05.04 implementation depends on it.
- Verify locks, ownership denial and immediate authority rechecks before P06.03/P07.02.
- Qualify interrupted applies, drift, partial effects and recovery at G07.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A provider or backend change alters planning/apply behavior, resource ownership moves between tools, or drift invalidates the approval model.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
