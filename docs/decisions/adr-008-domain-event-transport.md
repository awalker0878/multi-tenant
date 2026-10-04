# ADR-008 — Domain event transport

Owner role: Architecture/SRE leads. Related phases: P00, P01. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Domain events coordinate projections and work across PHP and Python services. The transport must support the product’s delivery and recovery semantics, but the register has not selected a broker. RabbitMQ is a candidate requiring assessment against actual event retention, replay, ordering, availability and team operation needs.

## Decision and scope

Domain-event transport; RabbitMQ candidate, assess delivery/ordering/replay/HA needs and team support.

Initial checkpoint: NOW: P00.03 before P01.03.

Refinement and validation: Actual outbox/inbox interoperability at G01; HA/retention/restore at G10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| RabbitMQ candidate | Assess routing, acknowledgment, retry, retention/replay design and the team’s ability to operate the required topology. |
| Log-oriented event transport | Assess consumer replay and retention needs against additional platform and partition-management responsibilities. |
| Database-backed delivery between services | Assess operational simplicity against coupling, fan-out, independent consumption and recovery limits. |

## Consequences

- The proposed delivery contract remains at least once, with publisher outbox and consumer inbox/deduplication behavior.
- Ordering promises are scoped to an identified aggregate or stream; consumers must handle duplicates and detect stale versions.

## Unresolved details and evidence needed

- Choose the transport and topology using representative PHP/Python publishers and consumers.
- Set message size, retention, retry/dead-letter ownership, poison-message handling and replay authorization.

## Acceptance and validation

- Demonstrate publish recovery after transaction commit and consumer restart at G01.
- Test duplicate, delayed, reordered and incompatible messages without violating aggregate invariants.
- Qualify broker outage, retention exhaustion and restore procedures at G10.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

Replay volume, ordering requirements, recovery objectives or operating capability invalidates the selected transport.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
