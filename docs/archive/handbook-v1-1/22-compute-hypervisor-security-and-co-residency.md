# 22. Compute, hypervisor security and co-residency

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:363 BEGIN -->

<a id="__RefHeading___Toc13333_1645000677"></a>
<a id="sec_22"></a>

<!-- SOURCE-BLOCK HB11:363 END -->

<!-- SOURCE-BLOCK HB11:364 BEGIN -->

Compute is a governed service with a profile for virtual hardware, boot mode, CPU/memory performance, host isolation, maintenance and recovery. Security zones are not collapsed merely to improve consolidation. Cyber Centre virtualization guidance strongly recommends that VMs from multiple security zones not share the same physical hardware. This handbook adopts zone-specific host pools as the on-premises baseline; any different model needs an explicit, documented assurance decision and qualified controls. \[[S03](77-appendix-h-primary-sources-and-implementation-references.md#S03), section 3\]

<!-- SOURCE-BLOCK HB11:364 END -->

<!-- SOURCE-BLOCK HB11:365 BEGIN -->


<a id="source-table-365"></a>

| Sharing case | Standard baseline | Enhanced / dedicated treatment |
| --- | --- | --- |
| Same tenant and logical domain | Shared hosts permitted within the qualified profile | Dedicated hosts where the threat/capacity profile requires |
| Different tenants, same zone class | Only approved same-zone assurance pool; independent domain and workload policies | Enhanced: dedicated WSD/domain security contexts; Dedicated: no unrelated tenant on assigned hosts |
| Different zone classes on one host | Not baseline; explicit assurance exception required | No automatic relaxation; dedicated pools as specified |
| MZ/control systems with tenant workloads | Separate management host pool | Independent management authority and recovery path |
| Security edge on workload compute | Only an explicitly qualified service-isolation design | Dedicated edge capacity/failure boundaries when required |
| Shared storage/fabric | Only where independently isolated and assessed | Physical/dedicated boundaries according to the exact profile |

<!-- SOURCE-BLOCK HB11:365 END -->

<!-- SOURCE-BLOCK HB11:366 BEGIN -->

The matrix distinguishes tenants from actual zones: two tenants labelled RZ do not thereby share a zone authority. Their shared host pool, if offered, is an explicit assurance choice. In HCI, separating VM placement without examining storage/controller and management co-residency is insufficient. Publish whether “dedicated” covers hosts only or also storage, edge and control infrastructure; no unstated shared dependency is hidden behind the label.

<!-- SOURCE-BLOCK HB11:366 END -->

<!-- SOURCE-BLOCK HB11:367 BEGIN -->

Secure boot, TPM/attestation, firmware integrity, supported host OS/hypervisor, restricted management services, controlled consoles and VM isolation form the host baseline where required/supported by the profile. CPU compatibility, NUMA alignment, huge pages, reservations, device passthrough and accelerators are declared capabilities, not implicit guarantees. Overcommit policy separates requested, reserved and consumed resources. Evacuation, live migration and HA restart must preserve all placement restrictions or stop safely when capacity is insufficient.

<!-- SOURCE-BLOCK HB11:367 END -->

<!-- SOURCE-BLOCK HB11:368 BEGIN -->

<a id="req_CMP_001"></a>

CMP-001  Compute placement, maintenance evacuation, migration and HA restart SHALL enforce the approved tenant/domain/zone co-residency matrix; no scheduler action SHALL silently weaken it.

<!-- SOURCE-BLOCK HB11:368 END -->

<!-- SOURCE-BLOCK HB11:369 BEGIN -->

Platform engineering  \|  Verify: [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-056](73-appendix-d-conformance-test-catalogue.md#test_CT_056)  \|  Basis: [S03](77-appendix-h-primary-sources-and-implementation-references.md#S03)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:369 END -->

<!-- SOURCE-BLOCK HB11:370 BEGIN -->

<a id="req_CMP_002"></a>

CMP-002  Each compute profile SHALL define supported hardware/software, boot/attestation controls, administrative isolation, resource guarantees, overcommit policy and handling of unsupported devices.

<!-- SOURCE-BLOCK HB11:370 END -->

<!-- SOURCE-BLOCK HB11:371 BEGIN -->

Platform engineering  \|  Verify: [CT-036](73-appendix-d-conformance-test-catalogue.md#test_CT_036), [CT-039](73-appendix-d-conformance-test-catalogue.md#test_CT_039), [CT-073](73-appendix-d-conformance-test-catalogue.md#test_CT_073)  \|  Basis: [S03](77-appendix-h-primary-sources-and-implementation-references.md#S03) / [S07](77-appendix-h-primary-sources-and-implementation-references.md#S07)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:371 END -->

<!-- SOURCE-BLOCK HB11:372 BEGIN -->

<a id="req_CMP_003"></a>

CMP-003  The meaning of dedicated compute SHALL state its exact physical and administrative scope and disclose any shared storage, network, control, support or recovery dependency.

<!-- SOURCE-BLOCK HB11:372 END -->

<!-- SOURCE-BLOCK HB11:373 BEGIN -->

Architecture authority  \|  Verify: [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:373 END -->

[Previous chapter](24-part-iii-portable-hosting-services.md) · [Chapter index](README.md) · [Next chapter](23-storage-data-services-and-copy-lineage.md)
