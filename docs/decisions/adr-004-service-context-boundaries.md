# ADR-004 — Service context boundaries

Owner role: Architecture lead. Related phases: P00. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `ACCEPTED` for the P01 development baseline as recorded in the [decision register](decision-register.md).

Reviewer: the requesting user, accountable G00 reviewer. Decision time: `2026-10-04T17:23:57-04:00`. The [G00 decision](../qualification/gate-reviews/g00-user-decision-2026-10-04.md) accepts the context and ownership baseline for P01 implementation. Boundary checks on actual service code and contracts remain required; acceptance does not claim implemented services or native qualification.

## Context

The product combines user interaction, governance, desired application structure, observed inventory, planning, execution and assurance. Without explicit data ownership, these responsibilities could recreate a distributed shared database and couple releases through undocumented behavior. Six business contexts allocate authority before API scaffolding; the console is a separate presentation/composition boundary.

## Decision and scope

Six business contexts: governance, catalogue, inventory, planning, lifecycle and assurance; Laravel assurance. The console composes their user experience and owns its session/presentation state. The initial deployment still has seven principal applications. A context, capability module, runtime process and independently deployed service are distinct concepts; their initial mapping is explicit in the [context code structure](../architecture/context-code-structure.md).

Initial checkpoint: P00.02 / G00.02 ownership baseline accepted by the recorded G00 decision before contract scaffolding.

Refinement and validation: Review boundary changes through owning ADR and contract impact.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Six business contexts plus console composition | Makes business ownership explicit and separates planning from execution, evidence and presentation. |
| Fewer deployables containing several contexts | May reduce early operating overhead, but still requires separate internal ownership and an explicit consolidation decision. |
| A deployable for every capability | Provides fine deployment boundaries at the cost of more contracts, operating dependencies and failure paths. |

## Consequences

- Console, governance, catalogue, inventory, planning, lifecycle and assurance each own their assigned data and write operations.
- Cross-context access uses owned interfaces; assurance is a Laravel service and must preserve evidence responsibilities independently of UI concerns.
- [ADR-024](adr-024-pragmatic-laravel-domain-convention.md) selects the pragmatic Laravel convention within the context-oriented source structure and code controls. Framework models and internal use cases remain private to their owning context; capability modules do not acquire independent service authority.

## Unresolved details and evidence needed

- Apply the accepted one-writer assignments for approvals, operation status, discovered resources and evidence finalization from the [domain review](../implementation/p00-domain-review.md); resolve new ambiguity before changing a contract.
- Define permitted dependencies and the event/API boundary for each cross-service user journey.

## Acceptance and validation

- Trace the worked application example to a single write owner for every record.
- Reject service designs that require cross-service database writes or circular synchronous transactions.
- Review contract and migration impact before moving an aggregate between contexts.

The reviewer and decision reference are recorded above. Record implementation and gate outcomes in the delivery register; accepting this ADR does not complete a work package.

## Revisit conditions

A measured delivery or operating constraint requires a boundary change, or an invariant cannot be maintained by the proposed owner without cyclic coordination.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
