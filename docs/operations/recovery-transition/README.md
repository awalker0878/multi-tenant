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
DESIGN DEVELOPMENT  /  OPS

## Operations, Recovery and Transition Playbook

*Operate the actual service envelope, recover dependencies, and retire without losing data or authority.*

Kit release v1.1 • 17 September 2026 • Parent architecture v1.4 retained

Proposed engineering development. Reference examples, site decisions, actual observations and approval remain separate.

This supplement develops IK-07 and IK-10 and the existing recovery/retirement runbooks. It supplies dependency decisions, change handling, a worked recovery timeline and operational records. It does not replace an approved incident process, native product procedure or data-owner decision.

## Section navigation

[1. Operate service outcomes rather than isolated components](1-operate-service-outcomes-rather-than-isolated-components.md#OPS_01)

[2. Specify dependency loss before it becomes an incident](2-specify-dependency-loss-before-it-becomes-an-incident.md#OPS_02)

[3. Run maintenance and recover interrupted changes](3-run-maintenance-and-recover-interrupted-changes.md#OPS_03)

[4. Recover the service in dependency order](4-recover-the-service-in-dependency-order.md#OPS_04)

[5. Calculate the recovery critical path and data point](5-calculate-the-recovery-critical-path-and-data-point.md#OPS_05)

[6. Migrate and fail back without conflicting writers](6-migrate-and-fail-back-without-conflicting-writers.md#OPS_06)

[7. Retire live service separately from retained data](7-retire-live-service-separately-from-retained-data.md#OPS_07)

[8. Accept operational responsibility for the delivered scope](8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

Basis: linked RA/WD and role-kit sections retain their original authority. The elaborations, record formats and calculations in this supplement are local proposals, not new government requirements. D-source references identify freshly checked public mechanisms, not installed compatibility. Exact source locators are in 04\_Shared/development/source\_reviews.csv.
