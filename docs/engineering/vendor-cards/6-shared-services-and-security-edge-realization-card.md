# 6. Shared services and security-edge realization card

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Vendor_Realization_Cards.docx) · [Chapter index](README.md)

> **Source:** VRC — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 5e453a432a4b6c5af7d75ba266945bdb9e01118757cbeec1e15d81f92be32ab0 -->
<!-- SOURCE-BLOCK VRC:59 BEGIN -->

<a id="VC_06"></a>

<!-- SOURCE-BLOCK VRC:59 END -->

<!-- SOURCE-BLOCK VRC:60 BEGIN -->

These resources are required integrations, not incidental dependencies automatically supplied by the selected hypervisor provider.

<!-- SOURCE-BLOCK VRC:60 END -->

<!-- SOURCE-BLOCK VRC:61 BEGIN -->

Baseline and related records: [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [SVC §5](../../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md#SVC_s_005)  •  [WD §7](../../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md#WD14_S07)

<!-- SOURCE-BLOCK VRC:61 END -->

<!-- SOURCE-BLOCK VRC:62 BEGIN -->


<a id="source-table-62"></a>

| Service track | Native design and implementation receipt |
| --- | --- |
| Security edge | EC/SE or equivalent contexts, exactly scoped routes/interfaces/policy, joint boundary authority, required inspection, session behaviour, HA and management. |
| IPAM/name/time | Delegated address authority, reservations/leases, DNS forward/reverse and approved resolvers including needed TCP/UDP, time profile and ownership. |
| Identity and trust | Enterprise roles/federation, workload and runner identities, certificate lifecycle, key-use/admin/recovery scope and independent bootstrap. |
| Storage/data | Owned virtual disks, file/object endpoint authorization, shared backend implications, capacity/QoS, snapshots/replication and sanitization. |
| Backup/recovery | Capture orchestration versus transfer path, repository protection, catalogue/keys, retained-copy ownership and isolated useful restore. |
| Telemetry and supply | Attributable event collection, buffering/loss handling, authorized search/retention, trusted images/artifacts and publication authority. |

<!-- SOURCE-BLOCK VRC:62 END -->

<!-- SOURCE-BLOCK VRC:63 BEGIN -->

<!-- SOURCE-BLOCK VRC:63 END -->

<!-- SOURCE-BLOCK VRC:64 BEGIN -->

Each track publishes a handoff containing actual identity, permitted use, capacity/limits, support version, lifecycle owner, current acceptance restrictions and evidence. Sharing a reference does not require sharing the producer’s privileged credentials or full Terraform state.

<!-- SOURCE-BLOCK VRC:64 END -->

<!-- SOURCE-BLOCK VRC:65 BEGIN -->

SVC-REF is an illustrative shared-service domain, not permission for all provider traffic. Service-side return routing, source validation and backend entitlement remain part of qualification. Record each service’s compromise and outage dependency.

<!-- SOURCE-BLOCK VRC:65 END -->

<!-- SOURCE-BLOCK VRC:66 BEGIN -->

<!-- SOURCE-BLOCK VRC:66 END -->

[Previous chapter](5-physical-fabric-and-oob-realization-card.md) · [Chapter index](README.md) · [Next chapter](7-support-tuple-variations-and-evidence-checklist.md)
