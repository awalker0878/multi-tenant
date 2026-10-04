# ADR-014 — First native provisioning and migration slice

Owner role: Product/infrastructure leads. Related phases: P00. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the current recommendation for review. No accountable-owner acceptance or native qualification is claimed; the register disposition is unchanged.

## Context

The first usable native delivery needs a narrow route with observable application recovery. The current P00 assessment and the user’s 2026-10-04 clarification favor rebuilding a reproducible Linux application on OpenStack and restoring its complete consistent state from VMware. This replaces the earlier cold-conversion-first proposal.

The historical branch used a `REBUILD_RESTORE` application driver. Its design is reference information; the recommendation here follows the current application assessment and does not import old implementation, selected Ubuntu/tool versions, test results or native support. Exact target artifacts, capture/restore tooling, downtime and consistency behavior remain subject to feasibility.

## Decision and scope

Prefer OpenStack provisioning followed by VMware→OpenStack `application_rebuild_restore` for the selected rebuildable Linux stateful application, subject to feasibility. Build a clean target from pinned guest/application/configuration artifacts, capture and restore all state consistently, and admit final cutover only after source writer exclusion and target validation.

Whole-VM `cold_guest_disk_conversion_import` remains a separately scoped and qualified P09 option. Rebuild/restore does not satisfy a requirement to preserve an opaque VM or unsupported appliance.

Initial checkpoint: NOW: P00.04 / G00.04 confirms rebuildability, exact initial method and feasibility.

Refinement and validation: Discovery confirms assumptions at G04; separate native qualification at G07/G08; changed method needs revised scope.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Application rebuild and consistent data restore | Preferred for the first reproducible Linux application. Makes deployment artifacts and dataset recovery explicit; requires complete dependency/configuration/secret reconstruction and proven capture/restore compatibility. |
| Cold whole-VM conversion/import | Separate P09 option when application rebuild is unsuitable or VM preservation is required. Adds firmware/device/driver, disk-chain, encryption and target-boot qualification; it does not bypass application recovery obligations. |
| Application-native synchronization, warm or live VM movement | May reduce outage for suitable workloads but adds distinct consistency, convergence and cutover requirements. Each method needs its own implementation and qualification. |

## Consequences

- OpenStack provisioning and application migration have separate native gates; a successful empty target deployment does not qualify migration.
- First-route feasibility prioritizes reproducible deployment, complete consistent capture/restore, configuration/secret treatment, isolation and stateful cutover/recovery. Converter selection does not block this method.
- Final migration includes an explicit source quiescence/fencing and data boundary; target preparation before the window is not proof of zero outage.
- The source remains protected until application acceptance and a separate retirement decision. Pre-write source return and post-write recovery preserve different data boundaries.
- Every later whole-VM route has its own method identifier, exact tuple, campaign and support claim.

## Unresolved details and evidence needed

- Select the exact platform/guest/application/database/storage/network tuple and reproducible deployment artifacts.
- Select consistent capture/restore tooling; prove database/attachment completeness, required metadata, configuration and secret reconstruction.
- Define outage/data bounds, source fencing, first target-write observation, post-write recovery and application-owner participation.

## Acceptance and validation

- Complete [initial route feasibility](../qualification/feasibility/initial-route.md) at P00.04/G00.04 with explicit limitations.
- Reconfirm discovery assumptions at G04 and qualify provisioning separately at G07.
- At G08, verify stateful application behavior, data integrity, security and both recovery boundaries for `application_rebuild_restore` on the selected tuple.
- Qualify any P09 whole-VM expansion independently; no earlier method result transfers automatically.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

The application cannot be reproduced completely, capture/restore cannot preserve required state, the source/target tuple changes, or downtime/data requirements require a different method.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [P00 route and operating review](../implementation/p00-route-and-operations-review.md) — candidate input records, experiments and unresolved decisions.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.


The [engineering selection record](../implementation/p00-engineering-selections.md) now fixes this choice for reversible development at its stated scope. It does not supply missing operating facts, native authority or accountable acceptance.


## Bounded state-recovery observation

The [PostgreSQL/attachment fixture report](../implementation/p00-restore-fixture-results.md) now records actual consistent-state capture, clean restore, exact invalid-bundle rejection and both fixture recovery boundaries. It retains an initial archive-transfer failure and corrected locked execution. This is E2 real-dependency evidence at the declared fixture scope. It does not show the full application deployment/configuration, a particular installed source/target backend, independent native fencing or recovery after loss of uncaptured target state.

Use this result in the G00.04 bounded feasibility review alongside the pinned candidate/application profile and appropriate fixture review. Full E3 native provisioning/migration remains G07/G08; actual native effects require their own scoped authority. Method acceptance remains incomplete where the required application/profile/review evidence is absent.
