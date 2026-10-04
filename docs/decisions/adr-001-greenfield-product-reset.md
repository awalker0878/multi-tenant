# ADR-001 — Greenfield product reset

Owner role: Product lead. Related phases: P00. Record date: 2026-10-04.

Origin: `DIRECTED`. Disposition: `ACCEPTED` as recorded in the [decision register](decision-register.md).

The accepted disposition records explicit user direction already recorded in the register. It does not claim a new technical approval, completed compatibility proof or implementation acceptance.

## Context

The previous Laravel foundation and earlier runtime contain useful historical ideas but cannot define the new product implicitly. The user instructed the team to start a new enterprise microservices plan and abandon the previous foundation branch as the implementation baseline. A clean implementation must therefore make scope, ownership and acceptance explicit before adopting reference material.

## Decision and scope

Fresh implementation; previous Laravel foundation is superseded; old runtime is reference only.

Initial checkpoint: NOW: user direction already recorded; P00.01 scopes product.

Refinement and validation: G00 confirms release exclusions and no legacy runtime dependency.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Fresh product implementation | Accepted user direction. New services, data model and delivery evidence are established on the current greenfield branch. |
| Incremental extension of the previous foundation | Conflicts with the recorded reset unless the user explicitly revises that instruction. |
| Selective reuse of ideas or isolated components | Permissible only after review against the new requirements; prior completion status and runtime authority do not transfer. |

## Consequences

- The new repository structure and delivery register define the product baseline; reference branches remain historical inputs.
- Any retained data or import requirement is decided separately in ADR-021; a clean codebase does not establish that data may be discarded.

## Unresolved details and evidence needed

- List the exact release exclusions and the reference materials needed for P00.01.
- Identify every proposed reuse and whether it introduces runtime, schema, state or deployment coupling.

## Acceptance and validation

- Review the initial product scope and exclusions at G00.
- Inspect dependency and deployment manifests for unintended links to the superseded runtime.
- Require fresh verification and qualification references for each adopted capability.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A new explicit user direction changes the reset scope, or an identified mandatory retained-data obligation changes the implementation approach.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
