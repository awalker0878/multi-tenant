# Infrastructure reference architecture and cross-platform provisioning strategy

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->

## Chapters

- [1. Purpose, scope and architectural authority](1-purpose-scope-and-architectural-authority.md)
- [2. Design drivers and selected reference pattern](2-design-drivers-and-selected-reference-pattern.md)
- [3. System context and physical hosting topology](3-system-context-and-physical-hosting-topology.md)
- [4. Hosting cells, resource pools and failure boundaries](4-hosting-cells-resource-pools-and-failure-boundaries.md)
- [5. Physical fabric and platform attachment](5-physical-fabric-and-platform-attachment.md)
- [6. Management, platform control and out-of-band access](6-management-platform-control-and-out-of-band-access.md)
- [7. Tenant environments and security-domain placement](7-tenant-environments-and-security-domain-placement.md)
- [8. Zone interfaces, routing and security-edge topology](8-zone-interfaces-routing-and-security-edge-topology.md)
- [9. Shared services, ingress and controlled egress](9-shared-services-ingress-and-controlled-egress.md)
- [10. Addressing, name services and end-to-end traffic](10-addressing-name-services-and-end-to-end-traffic.md)
- [11. Compute pools, hypervisors and workload placement](11-compute-pools-hypervisors-and-workload-placement.md)
- [12. Storage, backup and data-isolation architecture](12-storage-backup-and-data-isolation-architecture.md)
- [13. Identity, cryptography and service trust](13-identity-cryptography-and-service-trust.md)
- [14. Availability, multi-site operation and recovery topology](14-availability-multi-site-operation-and-recovery-topology.md)
- [15. Cross-vendor realization model](15-cross-vendor-realization-model.md)
- [16. Nutanix hosting-stack reference realization](16-nutanix-hosting-stack-reference-realization.md)
- [17. VMware and NSX hosting-stack reference realization](17-vmware-and-nsx-hosting-stack-reference-realization.md)
- [18. OpenStack hosting-stack reference realization](18-openstack-hosting-stack-reference-realization.md)
- [19. Physical workloads and future platform extensions](19-physical-workloads-and-future-platform-extensions.md)
- [20. Provisioning model and infrastructure work packages](20-provisioning-model-and-infrastructure-work-packages.md)
- [21. Day-0 bootstrap and physical commissioning](21-day-0-bootstrap-and-physical-commissioning.md)
- [22. Vendor-platform and shared-service commissioning](22-vendor-platform-and-shared-service-commissioning.md)
- [23. Tenant, domain and workload provisioning sequence](23-tenant-domain-and-workload-provisioning-sequence.md)
- [24. Terraform across the vendor stacks](24-terraform-across-the-vendor-stacks.md)
- [25. Change, brownfield adoption and configuration ownership](25-change-brownfield-adoption-and-configuration-ownership.md)
- [26. Operating model, capacity and observability](26-operating-model-capacity-and-observability.md)
- [27. Recovery, migration and retirement](27-recovery-migration-and-retirement.md)
- [28. Architecture acceptance and verification](28-architecture-acceptance-and-verification.md)
- [29. Architecture decisions and alternatives](29-architecture-decisions-and-alternatives.md)
- [30. Implementation handoff and delivery sequence](30-implementation-handoff-and-delivery-sequence.md)
- [Appendix A — Revision scope and baseline traceability](31-appendix-a-revision-scope-and-baseline-traceability.md)
- [Appendix B — Infrastructure interface schedule](32-appendix-b-infrastructure-interface-schedule.md)
- [Appendix C — Architecture terminology](33-appendix-c-architecture-terminology.md)
- [Appendix D — Sources and review status](34-appendix-d-sources-and-review-status.md)
- [Appendix E — Linked engineering knowledge and decision map](35-appendix-e-linked-engineering-knowledge-and-decision-map.md)
- [v1.4 — Connected infrastructure design and acceptance](36-v1-4-connected-infrastructure-design-and-acceptance.md)

## Source front matter
<!-- SOURCE-BLOCK RA:0 BEGIN -->

<a id="V14_RA_START"></a>

INFRASTRUCTURE ARCHITECTURE  /  RA

<!-- SOURCE-BLOCK RA:0 END -->

<!-- SOURCE-BLOCK RA:1 BEGIN -->

v1.4 linked worked design: [WD — resources, paths, build receipts and acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

<!-- SOURCE-BLOCK RA:1 END -->

<!-- SOURCE-BLOCK RA:2 BEGIN -->

## Portable Multi-Tenant<br>Secure Hosting

<!-- SOURCE-BLOCK RA:2 END -->

<!-- SOURCE-BLOCK RA:3 BEGIN -->

*Infrastructure Reference Architecture and Cross-Platform Provisioning Strategy*

<!-- SOURCE-BLOCK RA:3 END -->

<!-- SOURCE-BLOCK RA:4 BEGIN -->

Draft v1.4  \|  16 September 2026

<!-- SOURCE-BLOCK RA:4 END -->

<!-- SOURCE-BLOCK RA:5 BEGIN -->

The selected infrastructure topology, trust boundaries, vendor realizations and provisioning strategy. Engineering detail is delegated to the linked supplements without making a custom automation application mandatory.

<!-- SOURCE-BLOCK RA:5 END -->

<!-- SOURCE-BLOCK RA:6 BEGIN -->


<a id="source-table-6"></a>

| Document control | Record |
| --- | --- |
| Document ID / parent | RA — parent architecture |
| Status | Proposed reference design and engineering guidance; adoption and qualification remain separate. |
| Baseline | Draft v1.2 infrastructure architecture, with retained v1.2 requirements and verification catalogues. |
| Audience | Infrastructure, security, network, platform, storage, service and operations owners; provisioning engineers. |
| Authority | Applicable external obligations and adopted controls prevail; supplements cannot silently weaken the parent. |
| Release boundary | Documentation and local document checks only. No live infrastructure deployment, qualification or authorization asserted. |

<!-- SOURCE-BLOCK RA:6 END -->

<!-- SOURCE-BLOCK RA:7 BEGIN -->

<!-- SOURCE-BLOCK RA:7 END -->

<!-- SOURCE-BLOCK RA:8 BEGIN -->

Engineering supplements: [GM — Architecture Gap Map and Design Decision Register](../../assurance/gap-map/1-document-family-scope-and-precedence.md#GM_s_001)  •  [NET — Fabric, Security Boundaries and Infrastructure Interfaces](../../engineering/fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [VND — Vendor-Stack Realizations and Common Reference Environment](../../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [PROV — Cross-Stack Provisioning and Commissioning Strategy](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)  •  [SVC — Shared Services, Data Protection and Recovery Architecture](../shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [QUAL — Site Design, Qualification and Operational Acceptance](../../assurance/site-qualification/1-from-proposed-architecture-to-accepted-service.md#QUAL_s_001)

<!-- SOURCE-BLOCK RA:8 END -->

<!-- SOURCE-BLOCK RA:9 BEGIN -->

Keep the eight Word files together after extracting the release package. Cross-document links use sibling filenames and stable bookmarks. START\_HERE.html provides an additional navigation index.

<!-- SOURCE-BLOCK RA:9 END -->

<!-- SOURCE-BLOCK RA:10 BEGIN -->

<!-- SOURCE-BLOCK RA:10 END -->

<!-- SOURCE-BLOCK RA:11 BEGIN -->

<a id="RA_summary"></a>

*Architecture summary*

<!-- SOURCE-BLOCK RA:11 END -->

<!-- SOURCE-BLOCK RA:12 BEGIN -->

The hosting service is a set of governed infrastructure environments. Sites contain resilient transport, protected management, provider-operated security and shared services, and bounded pools of native platform capacity. Tenants consume isolated compute, data and network resources within those foundations. A tenant, a workload security domain, a vendor cluster and a site are different boundaries. \[[B2](34-appendix-d-sources-and-review-status.md#RA_src_B2) §§3–7\]

<!-- SOURCE-BLOCK RA:12 END -->

<!-- SOURCE-BLOCK RA:13 BEGIN -->

The selected large-site pattern uses routed leaf/spine transport and independent Nutanix, VMware/NSX or OpenStack realizations. Each independent security-domain instance has its own routing and policy authority and an isolated handoff to the applicable ZIP/security service. Shared equipment does not imply shared routing, administrative permission or a proven independent failure domain. Privileged administration and recovery access remain separate from workload and service-consumption paths. \[[B2](34-appendix-d-sources-and-review-status.md#RA_src_B2) §§5–8, 15–18\]

<!-- SOURCE-BLOCK RA:13 END -->

<!-- SOURCE-BLOCK RA:14 BEGIN -->


<a id="source-table-14"></a>

| Architectural layer | Responsibility | Design boundary |
| --- | --- | --- |
| Site and hosting cell | Provide qualified physical and native platform capacity. | Actual failure, co-residency and management dependencies recorded. |
| Tenant and security domain | Define ownership, workload placement and controlled connectivity. | No implicit cross-tenant, inter-zone or management reachability. |
| Provider service and ZIP | Deliver selected service endpoints and governed trust transitions. | Consumption is distinct from administration and backend data entitlement. |
| Provisioning work packages | Establish foundations, allocate resources, verify and activate. | Supported tools execute under the appropriate infrastructure owner. |

<!-- SOURCE-BLOCK RA:14 END -->

<!-- SOURCE-BLOCK RA:15 BEGIN -->

<!-- SOURCE-BLOCK RA:15 END -->

<!-- SOURCE-BLOCK RA:16 BEGIN -->

Provisioning commissions physical and management foundations, then native platform and common-service capability, before ordinary tenant allocation. Terraform provisions supported resources across the selected hosting stack and required edge, address/name, data-protection and trust integrations. Native installers and lifecycle tools retain operations they own. A new custom portal, routing compiler or controller application is not a prerequisite. \[[B2](34-appendix-d-sources-and-review-status.md#RA_src_B2) §§20–24\]

<!-- SOURCE-BLOCK RA:16 END -->

<!-- SOURCE-BLOCK RA:17 BEGIN -->

The linked supplements turn remaining design questions into engineering records: NET explains actual paths and attachment accounting; VND maps the common reference environment to native stacks; PROV defines ownership and build order; SVC explains service/data/recovery dependencies; QUAL defines site measurements and acceptance; GM records the gaps and open decisions. None substitutes for actual supported versions, site values, executable integrations, measured qualification or formal authorization.

<!-- SOURCE-BLOCK RA:17 END -->

<!-- SOURCE-BLOCK RA:18 BEGIN -->

Read next: [System topology](3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [Vendor realization](15-cross-vendor-realization-model.md#RA_s_015)  •  [Provisioning work packages](20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [Gap and decision map](../../assurance/gap-map/3-detailed-gap-register-and-treatment.md#GM_s_003)

<!-- SOURCE-BLOCK RA:18 END -->

<!-- SOURCE-BLOCK RA:19 BEGIN -->

<!-- SOURCE-BLOCK RA:19 END -->

<a id="RA_contents"></a>

<!-- SOURCE-BLOCK RA:57 BEGIN -->

<!-- SOURCE-BLOCK RA:57 END -->

<!-- SOURCE-BLOCK RA:58 BEGIN -->

Use the contents and named section links to navigate. After later edits, update Word fields and verify pagination before release.

<!-- SOURCE-BLOCK RA:58 END -->

<!-- SOURCE-BLOCK RA:59 BEGIN -->

<!-- SOURCE-BLOCK RA:59 END -->

<!-- SOURCE-BLOCK RA:60 BEGIN -->

PART 1  /  Infrastructure purpose and topology

<!-- SOURCE-BLOCK RA:60 END -->
