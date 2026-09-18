# 5. Commission, qualify, prepare and activate

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/Worked_Delivery_Example.docx) · [Chapter index](README.md)

> **Source:** WDE — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: ae4ea65ea564fe848f214f5154ca4b67726eb6628d07a4b4f7714210e49ccd0d -->
<!-- SOURCE-BLOCK WDE:49 BEGIN -->

<a id="EX_05"></a>

<!-- SOURCE-BLOCK WDE:49 END -->

<!-- SOURCE-BLOCK WDE:50 BEGIN -->

Use the gate dependency rather than assuming that numeric gate order grants chronological permission.

<!-- SOURCE-BLOCK WDE:50 END -->

<!-- SOURCE-BLOCK WDE:51 BEGIN -->

Baseline and related records: [WD §9](../internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md#WD14_S09)  •  [DEL §3](../../governance/delivery-framework/3-apply-gate-dependencies-rather-than-numerical-order.md#DEL_03)  •  [IK §7](../../implementation/delivery-guide/7-tenant-provisioning-and-controlled-production-activation.md#IK_07)

<!-- SOURCE-BLOCK WDE:51 END -->

<!-- SOURCE-BLOCK WDE:52 BEGIN -->


<a id="source-table-52"></a>

| Stage | Example output | Still-required evidence |
| --- | --- | --- |
| G0 / architecture | ADR-EX-01 and selected service scope; tenant/domain/placement and failure constraints. | Actual adopted decision and applicable control responsibilities. |
| P0–P1 / G1 | Restricted recovery access and foundation transport/attachment capacity. | As-built physical and management observations; accepted inventory and actual owners. |
| P2/P3 installation | Selected native platform, denied boundaries and published provider-service endpoints. | Supported artifacts, native task/configuration receipts and exact tuple. |
| Restricted P4/P5 fixture | Disposable endpoints and temporary probe; routing, isolation, service and recovery tests. | Specific test authorization; actual observations rather than designed expectations. |
| G2 / qualification | Accepted service/capability envelope for the first stack. | Applicable passing observations, approved exceptions and measured limits. |
| G4 initial / readiness | Support, custody, telemetry, incident path and required restore proof ready. | Named owner decisions and evidence supporting the offered service promise. |
| Production P4/P5 / G3 | New authorized tenant instance; current tests, controlled exposure and handover confirmation. | Current prerequisite decisions, valid operating authority and reversible activation record. |
| P6 / continuing G4 | Changes, recovery exercises, migration or retirement. | Current as-built and requalification of materially changed scope. |

<!-- SOURCE-BLOCK WDE:52 END -->

<!-- SOURCE-BLOCK WDE:53 BEGIN -->

<!-- SOURCE-BLOCK WDE:53 END -->

<!-- SOURCE-BLOCK WDE:54 BEGIN -->

STEP-EX-01 cannot be executed from this book alone. The implementation copy must name the approved site LLD, actual resources, tool artifact, executor, credential custody, expected result, stop condition and data-safe recovery step.

<!-- SOURCE-BLOCK WDE:54 END -->

<!-- SOURCE-BLOCK WDE:55 BEGIN -->

<!-- SOURCE-BLOCK WDE:55 END -->

[Previous chapter](4-native-realization-and-provisioning-ownership.md) · [Chapter index](README.md) · [Next chapter](6-capacity-and-test-resource-accounting.md)
