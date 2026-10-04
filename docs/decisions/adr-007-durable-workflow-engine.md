# ADR-007 — Durable workflow engine

Owner role: Infrastructure lead. Related phases: P00, P01, P06. Record date: 2026-10-04.

Origin: `DIRECTED`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Provisioning and migration span outages, human approvals and external effects that can complete even when a response is lost. The register records a directed Temporal/Python baseline with PROPOSED disposition: runtime feasibility and operating ownership still require review. Lifecycle remains the admission and operation-journal owner.

## Decision and scope

Temporal/Python durable workflow baseline; lifecycle owns admission and operation journal.

Initial checkpoint: NOW: P00.03 confirms supported runtime/operation owner before P01.05.

Refinement and validation: Workflow/version/replay/failure model finalized before P06.02; G06/G10 proof.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Temporal/Python with lifecycle admission and journal | Separates durable workflow execution from business authorization while requiring clear reconciliation and versioning rules. |
| Database job runner with explicit state machine | Would require the team to own durable scheduling, replay/version compatibility and recovery mechanics; changing the directed baseline needs review. |
| Synchronous API or ordinary queue chain | Cannot be accepted without equivalent durable state, uncertainty and restart semantics for multi-step external operations. |

## Consequences

- Workflow history and the lifecycle operation journal have distinct responsibilities and a defined reconciliation relationship.
- Activities must tolerate retry and unknown outcomes; durable execution does not make an external native operation exactly once.

## Unresolved details and evidence needed

- Confirm the supported SDK/runtime set, operated service owner, namespace boundaries and backup/restore approach.
- Define workflow versioning, long-running upgrade handling, cancellation and activity reconciliation contracts.

## Acceptance and validation

- Prove deterministic replay and controlled workflow evolution before P06.02 completion.
- Inject worker loss and lost external responses and verify safe reconciliation without duplicated effects.
- Exercise workflow service recovery and journal consistency in G06/G10 campaigns.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

The selected runtime cannot be operated within deployment constraints, replay compatibility cannot be sustained, or recovery requirements exceed the chosen workflow service design.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
