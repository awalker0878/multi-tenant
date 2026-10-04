# ADR-014 — First native provisioning and migration slice

Owner role: Product/infrastructure leads. Related phases: P00. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The first usable native delivery needs a narrow route with observable application recovery. The proposal combines OpenStack provisioning with VMware-to-OpenStack cold conversion/import for one Linux stateful application. Exact versions, conversion tooling, downtime and consistency behavior remain subject to feasibility.

## Decision and scope

OpenStack provisioning and VMware→OpenStack cold conversion/import for one Linux stateful application, subject to feasibility.

Initial checkpoint: NOW: P00.04 / G00.04 chooses exact initial method and feasibility.

Refinement and validation: Discovery confirms assumptions at G04; separate native qualification at G07/G08; changed method needs revised scope.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Cold conversion/import for one Linux stateful application | Provides a bounded first route with explicit outage, source quiescence, transfer and target acceptance steps. |
| Application rebuild and data restore | May fit some workloads better but has different application and backup requirements; it must be scoped as a distinct method. |
| Continuous replication or warm migration | May reduce outage but adds synchronization and cutover complexity and requires separate qualification. |

## Consequences

- OpenStack provisioning and migration have separate native gates; a successful empty target deployment does not qualify migration.
- The source remains protected until application acceptance and an explicit retirement decision; rollback feasibility depends on data divergence.

## Unresolved details and evidence needed

- Select the exact platform/guest/storage/network tuple, conversion method and representative application.
- Define consistency boundaries, outage budget, rollback/failback limits and required application-owner participation.

## Acceptance and validation

- Complete method feasibility at P00.04/G00.04 with explicit limitations.
- Reconfirm discovery assumptions at G04 and qualify provisioning separately at G07.
- At G08, verify stateful application behavior, data integrity, security and recovery for the selected route.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

Feasibility fails, the source/target tuple changes, or downtime and consistency requirements require a different method.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
