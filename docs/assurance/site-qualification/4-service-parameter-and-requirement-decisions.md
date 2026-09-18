# 4. Service parameter and requirement decisions

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<!-- SOURCE-BLOCK QUAL:55 BEGIN -->

<a id="__RefHeading___Toc10039_1525915568"></a>
<a id="QUAL_s_004"></a>

<!-- SOURCE-BLOCK QUAL:55 END -->

<!-- SOURCE-BLOCK QUAL:56 BEGIN -->

Parent architecture: [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK QUAL:56 END -->

<!-- SOURCE-BLOCK QUAL:57 BEGIN -->

The service owner defines required outcomes with the relevant data, security and operations owners; engineering demonstrates feasibility. Do not replace an unfilled RTO, RPO, retention or isolation decision with a product default. A security availability-impact category is not an uptime percentage, and synchronous replication is not automatic proof of an application recovery objective. \[[B2](09-references-parent-basis-and-external-context.md#QUAL_src_B2) §14\]

<!-- SOURCE-BLOCK QUAL:57 END -->

<!-- SOURCE-BLOCK QUAL:58 BEGIN -->


<a id="source-table-58"></a>

| Parameter group | Decision to record | Required validation |
| --- | --- | --- |
| Service scope and category | Resource/service boundary; confidentiality, integrity and availability impact; explicit excluded classes. | Applicable control/placement envelope accepted by responsible authorities. |
| Availability objective | Measured endpoint/operation, success definition, observation interval, maintenance accounting and failure scope. | Observed service result under offered topology; exclusions visible. |
| Recovery objectives | RTO start/end milestones, RPO recoverable consistency point, target/site policy and acceptance owner. | Restore/failover includes actual dependencies and useful recovered data. |
| Performance and capacity | Guaranteed versus best-effort resource quantities, contention model and operating reserve. | Unit-consistent measurements under specified load/failure. |
| Retention and disposal | Data/copy/evidence retention, holds, custodians, key lifetime and disposition authority. | No premature key/copy loss; approved sanitization and remaining-copy record. |
| Privilege and protocols | Target scope, identity strength, sessions/revocation, protocol/crypto profile and exceptions. | Actual configuration, endpoint identity and loss/recovery behaviour. |
| Observation and cadence | Required events, forwarding/buffering, evidence freshness and recovery/review frequency. | One approved parameter source; test schedules refer to it rather than conflict. |

<!-- SOURCE-BLOCK QUAL:58 END -->

<!-- SOURCE-BLOCK QUAL:59 BEGIN -->

<!-- SOURCE-BLOCK QUAL:59 END -->

<!-- SOURCE-BLOCK QUAL:60 BEGIN -->

The decision record contains proposed and approved values, measurement method, rationale, exact target profile, owner, approving authority, effective/review dates and impacts on dependent services. Reassessment follows material changes, not only a calendar date. A tighter service promise can require more independent capacity or a different platform; it cannot be obtained by relabelling the same untested topology.

<!-- SOURCE-BLOCK QUAL:60 END -->

<!-- SOURCE-BLOCK QUAL:61 BEGIN -->

Proposed examples in older material are not adopted values. Where inherited test procedures specify a cadence that differs from a subsequently approved service parameter, record the discrepancy and explicitly align the implementation test campaign. Do not silently change the historical procedure or select the more convenient schedule without authority.

<!-- SOURCE-BLOCK QUAL:61 END -->

<!-- SOURCE-BLOCK QUAL:62 BEGIN -->

Related engineering: [Open service decisions](../gap-map/3-detailed-gap-register-and-treatment.md#GM_s_003)  •  [Measured restore boundary](../../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md#SVC_s_005)

<!-- SOURCE-BLOCK QUAL:62 END -->

[Previous chapter](3-capacity-service-envelopes-and-growth-triggers.md) · [Chapter index](README.md) · [Next chapter](5-qualification-stages-applicability-and-evidence.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0019 — Separate information impacts from service-level and recovery promises](../../adr/0019-separate-information-impacts-from-service-level-and-recovery-promises.md)

<!-- END GENERATED DECISION LINKS -->
