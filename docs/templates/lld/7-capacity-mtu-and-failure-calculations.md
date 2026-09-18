# 7. Capacity, MTU and failure calculations

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/LLD_and_Engineering_Review_Template.docx) · [Chapter index](README.md)

> **Source:** ET — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b25a109f59a09baebb4dfc8c7f5069e9e98421ae5b009dba0e4b08117280511d -->
<a id="ET_07"></a>

Actual site values are required. Complete the response fields and identify controlled schedule/diagram references. Unknown or unsupported items remain blocking for their affected scope.

Baseline and related records: [QUAL §3](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [WD §11](../../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)


<a id="source-table-64"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Failure/load basis | Covered failure sets, simultaneous maintenance, workload mix and measurement conditions. | {{ET\_LOAD}} |
| Capacity calculation | Measured survivor capacity, reserve, existing commitment, new demand and units. | {{ET\_CAPACITY}} |
| Storage/performance | Protection/copy/rebuild overhead and latency/IOPS/throughput under contention. | {{ET\_PERF}} |
| MTU budget | Per-path workload size, all headers/options/tags and smallest surviving limit. | {{ET\_MTU}} |
| Recovery targets | Approved RTO/RPO and measurement boundaries; restore/failback method. | {{ET\_RTO}} |
| Margins/expansion | Binding bottleneck, growth/lead time, trigger and assigned owner. | {{ET\_GROWTH}} |

Review disposition: Draft until the actual engineering authority accepts the named scope. A checked form or calculator result does not establish live support, qualification or authorization.

[Previous chapter](6-management-services-and-trust.md) · [Chapter index](README.md) · [Next chapter](8-exact-platform-and-tool-operation-coverage.md)
