# ADR-006 — Service-owned persistence

Owner role: SRE/security leads. Related phases: P00, P01. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Applications need durable business records while preserving the proposed service ownership boundaries. Operated PostgreSQL with distinct service databases and roles is the proposed initial model. Logical separation does not settle whether a single physical cluster satisfies later trust, scale and recovery requirements.

## Decision and scope

Service-owned databases/roles on operated PostgreSQL; trust/scale may require separate clusters.

Initial checkpoint: NOW: P00.03 before P01.05.

Refinement and validation: Cross-service access denial at G01; physical separation/load/restore at G10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Service databases and roles on an operated PostgreSQL cluster | Limits initial platform overhead while requiring strict privileges and shared-failure analysis. |
| Separate PostgreSQL clusters for selected services or trust boundaries | Provides stronger operational separation but adds restore, patching and capacity responsibilities. |
| Shared schemas and direct cross-service queries | Makes integration convenient initially but undermines independent ownership, migrations and authorization boundaries. |

## Consequences

- Runtime roles receive only their owned data privileges; migration and backup roles require separately controlled authority.
- Cross-service read models are populated through contracts and must identify freshness and reconciliation behavior.

## Unresolved details and evidence needed

- Select database topology, connection budgets, encryption/custody and migration role lifecycle.
- Define per-service recovery objectives and determine whether shared physical failure is acceptable.

## Acceptance and validation

- Demonstrate cross-service access denial and owned migrations at G01.
- Restore a representative service and reconcile downstream projections without granting foreign writes.
- Qualify physical separation, load and recovery requirements at G10 before making availability claims.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

Trust policy, measured load, noisy-neighbor behavior or restore requirements exceed the chosen physical topology.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
