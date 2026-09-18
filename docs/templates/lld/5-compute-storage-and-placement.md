# 5. Compute, storage and placement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/LLD_and_Engineering_Review_Template.docx) · [Chapter index](README.md)

> **Source:** ET — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b25a109f59a09baebb4dfc8c7f5069e9e98421ae5b009dba0e4b08117280511d -->
<!-- SOURCE-BLOCK ET:47 BEGIN -->

<a id="ET_05"></a>

<!-- SOURCE-BLOCK ET:47 END -->

<!-- SOURCE-BLOCK ET:48 BEGIN -->

Actual site values are required. Complete the response fields and identify controlled schedule/diagram references. Unknown or unsupported items remain blocking for their affected scope.

<!-- SOURCE-BLOCK ET:48 END -->

<!-- SOURCE-BLOCK ET:49 BEGIN -->

Baseline and related records: [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)

<!-- SOURCE-BLOCK ET:49 END -->

<!-- SOURCE-BLOCK ET:50 BEGIN -->


<a id="source-table-50"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Compute pools | Actual host eligibility, resource class and approved co-residency decision. | {{ET\_COMPUTE}} |
| Scheduling/recovery | Placement, affinity, evacuation/HA restart, CPU/device compatibility and supported limits. | {{ET\_SCHED}} |
| Images and guests | Image digest, boot/drivers/hardening and guest/application responsibilities. | {{ET\_IMAGES}} |
| Storage class | Backend, disk/file/object identity, usable capacity/performance and authorization. | {{ET\_STORAGE}} |
| Copy/key lineage | Snapshots, clones, replicas, encryption context, key use/custody and retention. | {{ET\_COPIES}} |
| Protection/reuse | Capture/restore, independent repositories and approved media/key-scope sanitization. | {{ET\_PROTECTION}} |

<!-- SOURCE-BLOCK ET:50 END -->

<!-- SOURCE-BLOCK ET:51 BEGIN -->

<!-- SOURCE-BLOCK ET:51 END -->

<!-- SOURCE-BLOCK ET:52 BEGIN -->

Review disposition: Draft until the actual engineering authority accepts the named scope. A checked form or calculator result does not establish live support, qualification or authorization.

<!-- SOURCE-BLOCK ET:52 END -->

<!-- SOURCE-BLOCK ET:53 BEGIN -->

<!-- SOURCE-BLOCK ET:53 END -->

[Previous chapter](4-routes-zips-and-permitted-flows.md) · [Chapter index](README.md) · [Next chapter](6-management-services-and-trust.md)
