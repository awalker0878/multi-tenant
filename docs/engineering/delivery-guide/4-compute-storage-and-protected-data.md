# 4. Compute, storage and protected data

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Kit.docx) · [Chapter index](README.md)

> **Source:** EK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 0aeb8ee0a114d3ed23e97c684cc9812a0fa6ea5252e49f0c902132bf4e053a7d -->
<!-- SOURCE-BLOCK EK:41 BEGIN -->

<a id="EK_04"></a>

<!-- SOURCE-BLOCK EK:41 END -->

<!-- SOURCE-BLOCK EK:42 BEGIN -->

Bind resources to the approved isolation and failure scopes before sizing or placement. Include maintenance evacuation, restart and restore, not only initial VM creation.

<!-- SOURCE-BLOCK EK:42 END -->

<!-- SOURCE-BLOCK EK:43 BEGIN -->

Baseline and related records: [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [WD §7](../../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md#WD14_S07)  •  [ET §5](../../templates/lld/5-compute-storage-and-placement.md#ET_05)

<!-- SOURCE-BLOCK EK:43 END -->

<!-- SOURCE-BLOCK EK:44 BEGIN -->


<a id="source-table-44"></a>

| Layer | Detailed engineering content |
| --- | --- |
| Host pools | Actual eligible hosts/clusters, zone/domain sharing, hardware/CPU compatibility, reservations, scheduling/anti-affinity and restart constraints. |
| VM/image profile | Approved template/image digest, guest OS/driver/tooling, boot mode, vCPU/memory, virtual devices, management and guest configuration owner. |
| Virtual disks | Owned volume/backing policy, attachment authority, encryption/key context, performance class and snapshots/clone restrictions. |
| Guest data services | Selected block/file/object protocol, tenant namespace/ACL/policy, endpoint, credential scope, quotas and access-path control. |
| Backend data movement | Replication/rebuild membership, latency/loss limits, failure reserve, encryption as required and management boundaries. |
| Protected copies | Capture consistency, schedule/retention/hold, independent administration, catalogue/key location, restore path and disposal. |

<!-- SOURCE-BLOCK EK:44 END -->

<!-- SOURCE-BLOCK EK:45 BEGIN -->

<!-- SOURCE-BLOCK EK:45 END -->

<!-- SOURCE-BLOCK EK:46 BEGIN -->

Do not add backend replication or hypervisor key access to the guest firewall permit list. A virtual-disk read can be mediated by the hypervisor/storage stack without using the guest NIC. A file/object client inside the guest uses its approved network and data-service authorization path.

<!-- SOURCE-BLOCK EK:46 END -->

<!-- SOURCE-BLOCK EK:47 BEGIN -->

Calculate usable storage with the selected protection layout, growth, snapshots and rebuild headroom. Do not equate provisioned virtual capacity, physical used capacity, replicas and backups. Record how the chosen service behaves during contention and degraded operation.

<!-- SOURCE-BLOCK EK:47 END -->

<!-- SOURCE-BLOCK EK:48 BEGIN -->

<!-- SOURCE-BLOCK EK:48 END -->

[Previous chapter](3-addressing-routing-policy-and-attachment-schedules.md) · [Chapter index](README.md) · [Next chapter](5-management-and-shared-service-interfaces.md)
