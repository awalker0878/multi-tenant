# 4. Security, management and co-residency decisions

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Architecture_Kit.docx) · [Chapter index](README.md)

> **Source:** AK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: f0cd99f187d5f883e0f752e07de20f8878bef02fa1d0b36817674ef59bfd9802 -->
<!-- SOURCE-BLOCK AK:43 BEGIN -->

<a id="AK_04"></a>

<!-- SOURCE-BLOCK AK:43 END -->

<!-- SOURCE-BLOCK AK:44 BEGIN -->

Record the security decision at every shared layer. Separate a tenant name, a zone class, an independently governed zone/domain and the native routing object that realizes it.

<!-- SOURCE-BLOCK AK:44 END -->

<!-- SOURCE-BLOCK AK:45 BEGIN -->

Baseline and related records: [RA §6](../reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §7](../reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §8](../reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [AT §7](../../templates/hld/7-threat-sharing-and-responsibility-review.md#AT_07)

<!-- SOURCE-BLOCK AK:45 END -->

<!-- SOURCE-BLOCK AK:46 BEGIN -->


<a id="source-table-46"></a>

| Layer | Question that must be answered |
| --- | --- |
| Compute and hypervisor | Which domains may share a host or cluster, and do placement, evacuation and HA restart preserve that decision? |
| Storage and protection | Are disks, controllers, replicas, copies, key scopes or backup administrators shared? What prevents cross-scope attachment and destruction? |
| Routing and ZIP | Which two authorities approve a relationship? Where are forward/reply traffic and required inspection enforced? |
| Management and OOB | Which authority can administer each target? Does emergency access survive the specific production failure? |
| Shared services | Is consumption distinct from management and backend entitlement? Can a compromised service abuse permitted sessions? |
| Automation and supplier access | Who can change native resources, where do credentials operate, and how are temporary privileges and diagnostics controlled? |

<!-- SOURCE-BLOCK AK:46 END -->

<!-- SOURCE-BLOCK AK:47 BEGIN -->

<!-- SOURCE-BLOCK AK:47 END -->

<!-- SOURCE-BLOCK AK:48 BEGIN -->

Retain the v1.4 zone-aware host-pool baseline and explicit alternative approval. “Same RZ label” alone does not justify co-residency. “Dedicated” must identify which of host, cluster, storage, edge, management, backup and key custody is actually dedicated.

<!-- SOURCE-BLOCK AK:48 END -->

<!-- SOURCE-BLOCK AK:49 BEGIN -->

Cloud zoning guidance distinguishes logical ZIP functions and management-connected versus data-path interfaces; a product object by itself is not the whole control design. The kit uses that as source context, not as a substitute for an adopted control profile. \[K01\]

<!-- SOURCE-BLOCK AK:49 END -->

<!-- SOURCE-BLOCK AK:50 BEGIN -->

External mechanism context: [K01 — Cloud network security zones (ITSP.80.023)](https://www.cyber.gc.ca/en/guidance/cloud-network-security-zones-itsp80023)

<!-- SOURCE-BLOCK AK:50 END -->

<!-- SOURCE-BLOCK AK:51 BEGIN -->

<!-- SOURCE-BLOCK AK:51 END -->

[Previous chapter](3-required-architecture-views.md) · [Chapter index](README.md) · [Next chapter](5-service-resilience-capacity-and-portability.md)
