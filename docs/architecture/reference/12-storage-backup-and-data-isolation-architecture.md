# 12. Storage, backup and data-isolation architecture

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:186 BEGIN -->

<a id="__RefHeading___Toc3662_865363315"></a>
<a id="RA_s_012"></a>

<!-- SOURCE-BLOCK RA:186 END -->

<!-- SOURCE-BLOCK RA:187 BEGIN -->

Storage is a set of governed data services, not a single datastore attached to all tenants. The reference supports block, file and object access where the selected platform or associated service provides the required semantics. Compute-facing storage attachment, guest-facing data access, backend replication and storage administration are separate paths with different controls.

<!-- SOURCE-BLOCK RA:187 END -->

<!-- SOURCE-BLOCK RA:188 BEGIN -->


<a id="source-table-188"></a>

| Storage path | Reference separation | Principal control |
| --- | --- | --- |
| VM virtual disk | Hypervisor-mediated attachment to an authorized backend object | Tenant/WSD ownership, attachment authorization, encryption and copy controls |
| Guest block/file/object client | Explicit tenant data-service interface | Network authorization plus protocol identity, namespace/ACL/policy enforcement |
| Backend replication/rebuild | Provider-only storage transport and member endpoints | Cluster membership, supported encryption, capacity and fault-domain placement |
| Snapshot/clone/export | Controlled management/data-mover operation | Copy lineage, destination authorization, category/location and retention inheritance |
| Storage administration | Protected management path | Least privilege and separation from tenant data consumption |
| Backup/recovery repository | Independent protection and recovery authority as required | Protected copies, keys/catalogue availability and deletion/hold controls |

<!-- SOURCE-BLOCK RA:188 END -->

<!-- SOURCE-BLOCK RA:189 BEGIN -->

<!-- SOURCE-BLOCK RA:189 END -->

<!-- SOURCE-BLOCK RA:190 BEGIN -->

A storage class defines usable capacity, access protocol, expected latency/throughput/IOPS, contention policy, availability/durability objectives, encryption and key scope, snapshot/clone behaviour, replication, backup and sanitization. Hardware labels such as all-flash or HCI do not substitute for those outcomes. Capacity planning includes replication or erasure overhead, rebuild reserve, snapshots, retained backups and degraded operation.

<!-- SOURCE-BLOCK RA:190 END -->

<!-- SOURCE-BLOCK RA:191 BEGIN -->

In HCI, separating guest VM placement does not by itself separate controller, disk or management dependencies. The design explicitly records which storage components are shared across pools and how authorization and confidentiality are enforced. A virtual disk operation is not assumed to traverse the guest network ZIP; the relevant boundary may be hypervisor authorization and backend isolation. A guest accessing a file share over IP follows the normal controlled data-service path.

<!-- SOURCE-BLOCK RA:191 END -->

<!-- SOURCE-BLOCK RA:192 BEGIN -->

## Data protection and recovery

<!-- SOURCE-BLOCK RA:192 END -->

<!-- SOURCE-BLOCK RA:193 BEGIN -->

Backup selection follows the workload service requirement and the platform’s supported capture mechanism. A backup proxy may use a management API for snapshot orchestration and a separate data path for transfer. The guest does not receive management access as a side effect. Backup administration and deletion authority are separated from routine production operation for copies designated independent or immutable.

<!-- SOURCE-BLOCK RA:193 END -->

<!-- SOURCE-BLOCK RA:194 BEGIN -->

Protection includes the data, backup catalogue, configuration and keys needed to restore it. Retained copies keep ownership, location, classification, consistency and disposal obligations even after the live WSD is retired. A copy is not considered recoverable merely because a backup job succeeded. An isolated restore must demonstrate useful data, required identity/key access and the selected recovery point and time.

<!-- SOURCE-BLOCK RA:194 END -->

<!-- SOURCE-BLOCK RA:195 BEGIN -->

The portable storage requirement describes necessary behaviour, not a promise that every S3-compatible endpoint or snapshot format is equivalent. Qualify required object operations, multipart handling, metadata, policy, versioning, retention and encryption semantics; qualify file identity/ACL and block attachment behaviour separately. Export and restore methods are included in the service’s exit design.

<!-- SOURCE-BLOCK RA:195 END -->

<!-- SOURCE-BLOCK RA:196 BEGIN -->

Release for reuse requires an approved sanitization method appropriate to media, key scope and retained copies. Deleting a volume record is not proof that snapshots, replicas, exported keys or caches were destroyed. NIST SP 800-88 Rev. 2 is a supporting technical reference; applicable organizational media-handling requirements remain authoritative. \[[S27](34-appendix-d-sources-and-review-status.md#RA_src_S27)\]

<!-- SOURCE-BLOCK RA:196 END -->

<!-- SOURCE-BLOCK RA:197 BEGIN -->

Related engineering: [SVC §4 — Storage, copies and retained-data ownership](../shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [SVC §5 — Backup capture, independent protection and isolated restore](../shared-services/5-backup-capture-independent-protection-and-isolated-restore.md#SVC_s_005)

<!-- SOURCE-BLOCK RA:197 END -->

[Previous chapter](11-compute-pools-hypervisors-and-workload-placement.md) · [Chapter index](README.md) · [Next chapter](13-identity-cryptography-and-service-trust.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0027 — Separate virtual-disk, guest-data, replication and administration paths](../../adr/0027-separate-virtual-disk-guest-data-replication-and-administration-paths.md)
- [ADR-0028 — Protect backup administration and prove isolated usable restore](../../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md)

<!-- END GENERATED DECISION LINKS -->
