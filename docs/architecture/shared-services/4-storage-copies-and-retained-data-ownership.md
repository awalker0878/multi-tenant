# 4. Storage, copies and retained-data ownership

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx) · [Chapter index](README.md)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->
<a id="__RefHeading___Toc8881_1525915568"></a>
<a id="SVC_s_004"></a>

Parent architecture: [RA §11](../reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §27](../reference/27-recovery-migration-and-retirement.md#RA_s_027)

A virtual disk has a different data path from a guest file or object client. The first is mediated by the hypervisor/storage stack; the second sends packets through the guest network and service boundary. Backend replication, rebuild and snapshot orchestration are additional provider paths. A single firewall rule cannot stand in for storage attachment, copy authorization and key scope. \[[B2](07-references-parent-basis-and-external-context.md#SVC_src_B2) §12\]


<a id="source-table-59"></a>

| Operation | Authoritative resource record | Required security outcome |
| --- | --- | --- |
| Provision/attach disk | Owner/WSD/domain eligibility, backend object, target endpoint and key context. | Foreign attachment denied; allowed attachment does not expose array management. |
| File/object access | Tenant namespace, service identity, protocol ACL/policy and endpoint. | Network access plus data entitlement; no cross-tenant enumeration by default. |
| Snapshot/clone | Parent object, creation/consistency point, new owner and intended destination. | Category, location, key and retention constraints survive copying. |
| Replicate/tier | Source, destination, consistency mode, location and failure dependencies. | Only approved locations/owners; capacity and key access support recovery. |
| Export/import | Supported format/subset, integrity record, target authorization and ACL/identity mapping. | No implicit downgrade or assumption that format conversion restores a working service. |
| Retire/reuse | All known copies, hold/retention, method, key exclusivity and verifying authority. | No premature loss of retained recovery; no prior tenant data accessible on reassignment. |

The example ledger below is symbolic: no real volume, backup or key has been created. It demonstrates why stopping a WSD and deleting all of its data are different completion states.


<a id="source-table-62"></a>

| Copy identity | Lineage and scope | Disposition after WSD-01 retirement |
| --- | --- | --- |
| VOL-01R | Owned virtual data disk for data-01 in D01R; key context K-01. | Stop live use and dispose only under approved retention/sanitization decision. |
| SNAP-01R-a | Snapshot derived from VOL-01R; inherited category/location/key conditions. | Remove or retain with explicit owner and expiry; do not lose it from inventory. |
| BKP-01R-a | Protected recovery copy captured through accepted method; catalogue CAT-01. | May outlive live WSD; preserve K-01 or required recoverable key version and catalogue access. |
| REP-01R-a | Optional approved recovery-site copy, only when that service is offered. | Record writer role and fencing; no accidental concurrent writable source/target. |
| HOLD-01 | Illustrative retained-copy obligation assigned to the data owner. | Blocks affected disposal, not necessarily retirement of all live compute. |

The ledger contains actual copy locations, access identities, encryption/key versions, creation/consistency point, retention or hold authority, and the operational owner who can recover it. A volume name or WSD tag alone is not sufficient where copies are exported or retained outside the primary platform. Shared-key destruction is not an acceptable proxy for deleting one tenant’s eligible copy.

For disposal, use an approved media-appropriate method and record its scope, verification, remaining copies and exceptions. NIST SP 800-88 Revision 2 is retained as supporting technical guidance, not a replacement for applicable organizational media handling. Deletion of a control-plane record alone does not demonstrate that all data was sanitized. \[[B2](07-references-parent-basis-and-external-context.md#SVC_src_B2) §12; [S27](07-references-parent-basis-and-external-context.md#SVC_src_S27)\]

Related engineering: [Capture and restore architecture](5-backup-capture-independent-protection-and-isolated-restore.md#SVC_s_005)  •  [Retirement sequence](../../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md#PROV_s_006)

The [storage data-lifecycle assurance gate](../../engineering/storage-data-lifecycle-assurance.md) turns the ownership/lineage, service-semantics, copy/hold and sanitization-procedure obligations into a fail-closed service-profile record. It does not replace the separate backup/restore assurance gate or the resource-specific sanitization receipt required at actual release/reuse.

[Previous chapter](3-identity-certificates-keys-and-independent-recovery.md) · [Chapter index](README.md) · [Next chapter](5-backup-capture-independent-protection-and-isolated-restore.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0027 — Separate virtual-disk, guest-data, replication and administration paths](../../adr/0027-separate-virtual-disk-guest-data-replication-and-administration-paths.md)
- [ADR-0033 — Separate live-service retirement from retained-data disposal](../../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<!-- END GENERATED DECISION LINKS -->
