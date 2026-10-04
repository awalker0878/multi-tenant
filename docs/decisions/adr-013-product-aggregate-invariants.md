# ADR-013 — Product aggregate invariants

Owner role: Product/architecture leads. Related phases: P00, P03, P05. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Tenant, WSD, SecurityDomain, DomainInstance, Application and Workload describe different business and placement responsibilities. Ambiguous cardinalities would create inconsistent APIs, authorization and deletion behavior. The draft domain model is an input to this open decision, not evidence that every invariant has been accepted.

## Decision and scope

Tenant/WSD/SecurityDomain/DomainInstance/Application/Workload cardinalities and sharing/deletion rules.

Initial checkpoint: NOW: P00.02 / G00.02 baseline invariants.

Refinement and validation: Aggregate constraints before P03.01; real placement semantics before P05.02.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Explicit aggregates with owned invariants and references | Keeps business identity separate from placement and makes authorization and lifecycle constraints reviewable. |
| Single deployment object containing all concepts | Reduces initial entities but conflates tenant policy, application identity and native realization. |
| Mirror native platform inventory directly | Simplifies discovery mapping but makes the product model depend on provider structure and weakens portable intent. |

## Consequences

- Catalogue owns desired application structure; inventory observations and native identifiers remain separately sourced facts.
- Cross-aggregate deletion and sharing need an explicit lifecycle protocol rather than implicit cascading writes across services.

## Unresolved details and evidence needed

- Resolve each cardinality, uniqueness boundary, shared attachment rule and reassignment restriction.
- Specify deletion eligibility, retained historical references and how domain instances realize policy at sites.

## Acceptance and validation

- Review valid and invalid model examples at G00.02.
- Verify owned aggregate constraints before P03.01 and reject ambiguous tenant ownership.
- Validate the model against real placement cases before P05.02.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A required application or site topology cannot be represented without breaking an invariant, or a proposed sharing rule changes the authorization boundary.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
