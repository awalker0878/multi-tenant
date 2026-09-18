# 5. Backup capture, independent protection and isolated restore

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx) · [Chapter index](README.md)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->
<a id="__RefHeading___Toc8883_1525915568"></a>
<a id="SVC_s_005"></a>

The promised restore and recovery capability is part of readiness before the corresponding production service is activated. Later recurring exercises maintain that assurance; they are not a reason to accept an unproved initial service promise. The gate dependency is defined in WD §9 and QUAL.

Parent architecture: [RA §12](../reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §14](../reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §22](../reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §27](../reference/27-recovery-migration-and-retirement.md#RA_s_027)

Backup architecture has an orchestration path, a data path, a repository/copy path and a restoration path. A proxy may call a platform management API for snapshot orchestration while moving data through a different supported interface. That does not grant the tenant guest access to the management API. Capture methods are selected for the actual platform, consistency requirement and supported protection product; no universal API/agent mode is assumed. \[[B2](07-references-parent-basis-and-external-context.md#SVC_src_B2) §§12, 22\]


<a id="source-table-71"></a>

| Backup plane | Reference boundary | Key design record |
| --- | --- | --- |
| Capture orchestration | Scoped protection identity to the required platform/guest interface. | Permitted snapshot/quiesce/read operations, exact target scope and credential lifecycle. |
| Data transfer | Approved agent/proxy/data-mover connection; direction and performance declared. | Network path, source/destination identity, encryption and necessary temporary access. |
| Repository and copy protection | Recovery copy isolated from routine production destruction where required. | Immutability/retention mechanism, custodians, location, keys and accessible catalogue. |
| Restore administration | Separate authorized recovery operation and target selection. | Data owner, consistency point, eligible target domain/pool and activation authority. |
| Restored service | Initially isolated endpoint/data attachments with approved essential services. | Integrity, risk posture, identity/key renewal, application/data acceptance and measured timing. |

A protected copy is not independent merely because it has a different name or repository. Examine whether a compromised production administrator can delete it, shorten retention, destroy its key or remove the only catalogue. Record which protections are technically enforced and which are custodial/operational. Recovery access must remain possible for authorized owners without granting routine production credentials those destructive powers.


<a id="source-table-74"></a>

| Restore step | Deliverable | Acceptance observation |
| --- | --- | --- |
| Choose and authorize | Owner-approved copy and recoverable consistency point; target eligible under same security/location rules. | Catalogue, key and copy integrity accessible through trusted recovery path. |
| Prepare isolated target | Denied/quarantined target domains and owned compute/storage; essential services only. | No accidental production or cross-tenant connection. |
| Recover data and configuration | Supported restore with retained ownership and appropriate drivers/boot/identity. | Useful data/consistency markers, correct target access and key context. |
| Validate service | Infrastructure checks plus accountable workload/data-owner functional acceptance. | RPO at recovered consistent point and RTO at agreed service boundary measured. |
| Reconnect deliberately | Approved routes/names/exposure changed after isolation and consistency acceptance. | Actual post-activation path works; old writer/session authority controlled. |
| Close or retain exercise | Temporary connections/credentials removed and recovery evidence stored. | No orphan grants/copies; remaining retained test data explicitly owned. |

The parent requires useful restore evidence, not simply a successful backup job. The service class must define whether the claim is crash-consistent, application-consistent or another approved recovery point. Infrastructure staff cannot infer business correctness from a booting VM. A named workload/data owner accepts the restored content without turning this guide into the design of that application.

Related engineering: [RTO/RPO and retention decisions](../../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)  •  [Recovery qualification scope](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

[Previous chapter](4-storage-copies-and-retained-data-ownership.md) · [Chapter index](README.md) · [Next chapter](6-failure-recovery-migration-and-failback-topology.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0028 — Protect backup administration and prove isolated usable restore](../../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md)

<!-- END GENERATED DECISION LINKS -->
