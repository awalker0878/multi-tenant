# 28. Availability and recovery service profiles

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:428 BEGIN -->

<a id="__RefHeading___Toc13345_1645000677"></a>
<a id="sec_28"></a>

<!-- SOURCE-BLOCK HB11:428 END -->

<!-- SOURCE-BLOCK HB11:429 BEGIN -->

Define service reliability in measurable terms: what endpoint or operation is measured, success criteria, measurement window, permitted maintenance treatment, failure-domain tolerance, degraded behavior and owner. RTO is the target elapsed recovery time for a declared scope; RPO is the tolerated age/data-loss interval for the recovered state. Neither is inferred solely from a storage replication mode or a security “Medium” label.

<!-- SOURCE-BLOCK HB11:429 END -->

<!-- SOURCE-BLOCK HB11:430 BEGIN -->


<a id="source-table-430"></a>

| Profile field | Required interpretation |
| --- | --- |
| serviceObjectivePercent / window | Explicit indicator and monthly or other defined observation period; no hidden maintenance exclusions |
| failureTolerance / placement | Named node, rack, edge or site failures and minimum independently available capacity |
| recovery scope / RTO / RPO | Application/service boundary, start/end milestones, consistency point and measured evidence |
| maintenance / degraded mode | Drain, approved interruption, admission restrictions, customer notification and recovery rules |
| dependency budgets | DNS, IdP, KMS, storage, network, control plane and external-service assumptions |
| exercise cadence / failback | Who proves recovery, how often, and how data ownership returns |

<!-- SOURCE-BLOCK HB11:430 END -->

<!-- SOURCE-BLOCK HB11:431 BEGIN -->

Reference values in Appendix F make the baseline testable but are proposed design targets. Platform certification records actual measured capability; service acceptance requires the owner to approve a profile whose dependencies can support it. A site-recovery RTO can still result in breaching an availability objective: report that breach rather than treating RTO as an automatic SLO exclusion. Capacity reservation includes the tolerated failure and planned maintenance scenario.

<!-- SOURCE-BLOCK HB11:431 END -->

<!-- SOURCE-BLOCK HB11:432 BEGIN -->

<a id="req_REL_001"></a>

REL-001  Availability and recovery profiles SHALL define measurement scope, SLO, failure tolerance, maintenance treatment, RTO/RPO, consistency, dependencies and test cadence; impact categorization SHALL NOT substitute for these values.

<!-- SOURCE-BLOCK HB11:432 END -->

<!-- SOURCE-BLOCK HB11:433 BEGIN -->

Service owner  \|  Verify: [CT-012](73-appendix-d-conformance-test-catalogue.md#test_CT_012), [CT-052](73-appendix-d-conformance-test-catalogue.md#test_CT_052), [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:433 END -->

<!-- SOURCE-BLOCK HB11:434 BEGIN -->

<a id="req_REL_002"></a>

REL-002  Recovery/HA capabilities SHALL be measured under the approved load and failure scenario before a platform offers the profile; reported SLOs SHALL disclose exclusions and actual breaches.

<!-- SOURCE-BLOCK HB11:434 END -->

<!-- SOURCE-BLOCK HB11:435 BEGIN -->

Operations/SRE  \|  Verify: [CT-012](73-appendix-d-conformance-test-catalogue.md#test_CT_012), [CT-039](73-appendix-d-conformance-test-catalogue.md#test_CT_039), [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054), [CT-056](73-appendix-d-conformance-test-catalogue.md#test_CT_056)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:435 END -->

[Previous chapter](27-backup-retention-and-isolated-restore.md) · [Chapter index](README.md) · [Next chapter](29-placement-data-location-and-sovereign-optionality.md)
