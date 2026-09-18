# Operations, recovery and transition playbook

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->

## Chapters

- [1. Operate service outcomes rather than isolated components](1-operate-service-outcomes-rather-than-isolated-components.md)
- [2. Specify dependency loss before it becomes an incident](2-specify-dependency-loss-before-it-becomes-an-incident.md)
- [3. Run maintenance and recover interrupted changes](3-run-maintenance-and-recover-interrupted-changes.md)
- [4. Recover the service in dependency order](4-recover-the-service-in-dependency-order.md)
- [5. Calculate the recovery critical path and data point](5-calculate-the-recovery-critical-path-and-data-point.md)
- [6. Migrate and fail back without conflicting writers](6-migrate-and-fail-back-without-conflicting-writers.md)
- [7. Retire live service separately from retained data](7-retire-live-service-separately-from-retained-data.md)
- [8. Accept operational responsibility for the delivered scope](8-accept-operational-responsibility-for-the-delivered-scope.md)

## Source front matter
<!-- SOURCE-BLOCK OPS:0 BEGIN -->

DESIGN DEVELOPMENT  /  OPS

<!-- SOURCE-BLOCK OPS:0 END -->

<!-- SOURCE-BLOCK OPS:1 BEGIN -->

## Operations, Recovery and Transition Playbook

<!-- SOURCE-BLOCK OPS:1 END -->

<!-- SOURCE-BLOCK OPS:2 BEGIN -->

*Operate the actual service envelope, recover dependencies, and retire without losing data or authority.*

<!-- SOURCE-BLOCK OPS:2 END -->

<!-- SOURCE-BLOCK OPS:3 BEGIN -->

Kit release v1.1 • 17 September 2026 • Parent architecture v1.4 retained

<!-- SOURCE-BLOCK OPS:3 END -->

<!-- SOURCE-BLOCK OPS:4 BEGIN -->

Proposed engineering development. Reference examples, site decisions, actual observations and approval remain separate.

<!-- SOURCE-BLOCK OPS:4 END -->

<!-- SOURCE-BLOCK OPS:5 BEGIN -->

This supplement develops IK-07 and IK-10 and the existing recovery/retirement runbooks. It supplies dependency decisions, change handling, a worked recovery timeline and operational records. It does not replace an approved incident process, native product procedure or data-owner decision.

<!-- SOURCE-BLOCK OPS:5 END -->

<!-- SOURCE-BLOCK OPS:6 BEGIN -->

## Section navigation

<!-- SOURCE-BLOCK OPS:6 END -->

<!-- SOURCE-BLOCK OPS:7 BEGIN -->

[1. Operate service outcomes rather than isolated components](1-operate-service-outcomes-rather-than-isolated-components.md#OPS_01)

<!-- SOURCE-BLOCK OPS:7 END -->

<!-- SOURCE-BLOCK OPS:8 BEGIN -->

[2. Specify dependency loss before it becomes an incident](2-specify-dependency-loss-before-it-becomes-an-incident.md#OPS_02)

<!-- SOURCE-BLOCK OPS:8 END -->

<!-- SOURCE-BLOCK OPS:9 BEGIN -->

[3. Run maintenance and recover interrupted changes](3-run-maintenance-and-recover-interrupted-changes.md#OPS_03)

<!-- SOURCE-BLOCK OPS:9 END -->

<!-- SOURCE-BLOCK OPS:10 BEGIN -->

[4. Recover the service in dependency order](4-recover-the-service-in-dependency-order.md#OPS_04)

<!-- SOURCE-BLOCK OPS:10 END -->

<!-- SOURCE-BLOCK OPS:11 BEGIN -->

[5. Calculate the recovery critical path and data point](5-calculate-the-recovery-critical-path-and-data-point.md#OPS_05)

<!-- SOURCE-BLOCK OPS:11 END -->

<!-- SOURCE-BLOCK OPS:12 BEGIN -->

[6. Migrate and fail back without conflicting writers](6-migrate-and-fail-back-without-conflicting-writers.md#OPS_06)

<!-- SOURCE-BLOCK OPS:12 END -->

<!-- SOURCE-BLOCK OPS:13 BEGIN -->

[7. Retire live service separately from retained data](7-retire-live-service-separately-from-retained-data.md#OPS_07)

<!-- SOURCE-BLOCK OPS:13 END -->

<!-- SOURCE-BLOCK OPS:14 BEGIN -->

[8. Accept operational responsibility for the delivered scope](8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

<!-- SOURCE-BLOCK OPS:14 END -->

<!-- SOURCE-BLOCK OPS:15 BEGIN -->

Basis: linked RA/WD and role-kit sections retain their original authority. The elaborations, record formats and calculations in this supplement are local proposals, not new government requirements. D-source references identify freshly checked public mechanisms, not installed compatibility. Exact source locators are in 04\_Shared/development/source\_reviews.csv.

<!-- SOURCE-BLOCK OPS:15 END -->

<!-- SOURCE-BLOCK OPS:16 BEGIN -->

<!-- SOURCE-BLOCK OPS:16 END -->
