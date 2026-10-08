# ADR-002 — Requested application stack

Owner role: Architecture lead. Related phases: P00. Record date: 2026-10-04.

Origin: `DIRECTED`. Disposition: `ACCEPTED` as recorded in the [decision register](decision-register.md).

The accepted disposition records explicit user direction already recorded in the register. It does not claim a new technical approval, completed compatibility proof or implementation acceptance.

## Context

The requested experience uses a Laravel web application with PHP and Python backend responsibilities, and Inertia 3, Vue 3, TypeScript, Tailwind 4 and Vite 8 in the browser delivery path. These choices are product direction. They do not by themselves prove that every requested version can be resolved and operated together.

## Decision and scope

Laravel/PHP and Python; Inertia 3, Vue 3, TypeScript, Tailwind 4 and Vite 8.

Initial checkpoint: NOW: requested stack binding; P00.03 tests compatibility.

Refinement and validation: Failed compatibility returns a concrete choice to user; no silent stack substitution.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Requested stack with validated exact versions | Accepted direction; P00.03 must establish a reproducible compatible version set. |
| Requested major versions with an explicit compatibility exception | Requires a concrete incompatibility report and a user decision before substitution. |
| Different web framework or frontend delivery model | Outside the accepted direction unless the user changes the requirement. |

## Consequences

- The console owns the browser session and frontend integration; Python services expose backend capabilities through service contracts.
- Dependency locks, production asset construction and runtime images must be tested together rather than approved independently.

## Unresolved details and evidence needed

- Resolve Laravel/PHP/Node/Python versions through ADR-003 and determine the supported integration package versions.
- Record browser targets, build environment restrictions and the handling of development-only dependencies.

## Acceptance and validation

- Build the production frontend and run it through the Laravel session and authorization path.
- Verify the PHP/Python contract example against the selected runtime set.
- Present any failed compatibility result with options and delivery impact before changing the directed stack.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A requested major version cannot meet required compatibility or support constraints, or the user explicitly changes the stack.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
