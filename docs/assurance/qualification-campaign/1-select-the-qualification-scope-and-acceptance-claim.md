# 1. Select the qualification scope and acceptance claim

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<a id="QCP_01"></a>

Qualification is evidence for a named service, topology, version and failure model. It is not a blanket certification of a product brand.

Design basis and related records: [QUAL §5](../site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)  •  [IK §6](../../implementation/delivery-guide/6-restricted-qualification-and-meaningful-observations.md#IK_06)  •  [DEL §3](../../governance/delivery-framework/3-apply-gate-dependencies-rather-than-numerical-order.md#DEL_03)


<a id="source-table-20"></a>

| Campaign scope | Select observations for | Permitted conclusion |
| --- | --- | --- |
| First platform | Actual foundations, domain isolation, service interfaces, lifecycle, failure/load and useful restore. | Only the tested service classes, families, topology and limits. A second qualified stack is not a prerequisite. |
| Second platform comparison | Same logical service outcomes on another eligible native realization. | Deployment equivalence for the compared scope, not automatic live migration. |
| Portability / exit | Actual image/data recovery, drivers/boot, identity/keys, network rebinding, cutover and operation. | Only the supported transfer and recovered-service claim demonstrated. |
| Routine change | Changed objects/paths and dependent critical controls under the accepted service envelope. | Acceptance of the changed scope; not a rerun of every destructive foundation test. |

Begin with an applicability record identifying requirement assertions, current component and design revisions, enabled address families, sharing, expected load and covered failure. Select test procedures because they observe those assertions, not because the catalogue has a fixed number of entries. Approved not-applicable dispositions need a reason tied to the offered scope.

A restricted non-production fixture may generate evidence while the platform remains a safeguarded candidate. Its permission names disposable data, allowed probes/faults, restoration, window and stop authority. It cannot supply production authority. Complete the relevant G2 qualification and initial G4 readiness before G3 production activation.

All Q11 cards in this document are NOT RUN. An expected result, source reference or document check is never an observed platform result.

Continue with: [QCP §8](8-close-defects-and-issue-a-scoped-campaign-disposition.md#QCP_08)  •  [PBS §9](../../engineering/platform-build/9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)

[Chapter index](README.md) · [Next chapter](2-size-and-control-the-qualification-fixture.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0017 — Separate reference adoption, technical qualification and authorization](../../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

<!-- END GENERATED DECISION LINKS -->
