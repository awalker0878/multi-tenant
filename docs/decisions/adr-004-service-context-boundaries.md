# ADR-004 — Service context boundaries

Owner role: Architecture lead. Related phases: P00. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The product combines user interaction, governance, desired application structure, observed inventory, planning, execution and assurance. Without explicit data ownership, these responsibilities could recreate a distributed shared database and couple releases through undocumented behavior. The proposed seven contexts allocate authority before API scaffolding.

## Decision and scope

Seven contexts: console, governance, catalogue, inventory, planning, lifecycle, assurance; Laravel assurance.

Initial checkpoint: NOW: P00.02 / G00.02 before contract scaffolding.

Refinement and validation: Review boundary changes through owning ADR and contract impact.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Seven bounded contexts in the register | Makes business ownership explicit and separates planning from execution and evidence. |
| Fewer deployables containing several contexts | May reduce early operating overhead, but still requires separate internal ownership and an explicit consolidation decision. |
| A deployable for every capability | Provides fine deployment boundaries at the cost of more contracts, operating dependencies and failure paths. |

## Consequences

- Console, governance, catalogue, inventory, planning, lifecycle and assurance each own their assigned data and write operations.
- Cross-context access uses owned interfaces; assurance is proposed as a Laravel service and must preserve evidence responsibilities independently of UI concerns.

## Unresolved details and evidence needed

- Review ambiguous ownership for approvals, operation status, discovered resources and evidence finalization.
- Define permitted dependencies and the event/API boundary for each cross-service user journey.

## Acceptance and validation

- Trace the worked application example to a single write owner for every record.
- Reject service designs that require cross-service database writes or circular synchronous transactions.
- Review contract and migration impact before moving an aggregate between contexts.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A measured delivery or operating constraint requires a boundary change, or an invariant cannot be maintained by the proposed owner without cyclic coordination.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
