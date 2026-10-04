# ADR-003 — Runtime and dependency baseline

Owner role: Engineering lead. Related phases: P00, P01. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The requested frontend stack leaves exact backend, runtime and patch versions unresolved. Laravel 13 and PHP 8.5 are current candidates in the register, not a verified bill of materials. Reproducible builds and upgrade responsibility require one reviewed set of runtime, package and image identifiers.

## Decision and scope

Laravel 13/PHP 8.5 candidates; exact Node/Python/runtime and dependency patches unresolved.

Initial checkpoint: NOW: P00.03 / G00.03 before P01.01.

Refinement and validation: Exact lock/image resolution, update policy and support lifecycle before G01.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Validate the proposed Laravel/PHP candidates | Keeps the proposed baseline while requiring dependency resolution, build and execution evidence. |
| Select another compatible supported backend version set | Can resolve a candidate incompatibility, but must still satisfy ADR-002 and document support and upgrade implications. |
| Allow each service to choose versions independently | Reduces coordination initially but enlarges the maintenance, compatibility and image qualification matrix. |

## Consequences

- Each deployable needs lockfiles, image digests and an accountable dependency update owner.
- A common initial runtime family limits the qualification matrix; exceptions must identify the service and reason.

## Unresolved details and evidence needed

- Resolve exact PHP, Laravel, Python, Node, package-manager and operating-system image versions.
- Document compatibility sources, vulnerability/update policy, mirror availability and support lifecycle boundaries.

## Acceptance and validation

- Build all initial deployables from clean lockfiles and captured image inputs before G01.
- Run cross-language schema and integration checks using the exact selected runtimes.
- Demonstrate a repeatable dependency update and rollback decision on a non-production branch.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A dependency reaches its accepted support boundary, an unresolved vulnerability changes acceptability, or a required integration invalidates the runtime combination.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
