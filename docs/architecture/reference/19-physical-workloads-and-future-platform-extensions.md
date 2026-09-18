# 19. Physical workloads and future platform extensions

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3676_865363315"></a>
<a id="RA_s_019"></a>

Bare-metal workloads use the same tenant, domain and service requirements but a different attachment and lifecycle path. Their network may be realized directly by the physical fabric, so creating a new physical routing or attachment context can be an authorized foundation operation. This is a declared service class, not a hidden violation of the routine-overlay no-switch-change objective.

The reference physical-workload pattern includes authenticated hardware management, approved boot and firmware, controlled port membership, an explicit gateway/security-edge path, authorized storage access and media sanitization before reuse. Provider bootstrap traffic is separated from ordinary tenant data. A tenant does not receive unrestricted BMC, switch-port or storage-array authority merely because it has exclusive use of a server.

Container hosting is an extension with separately qualified cluster control, node isolation, workload admission, networking and storage. A namespace by itself is not accepted as a hostile-tenant security boundary. The extension must decide whether tenants share nodes or control planes and identify the actual network-policy enforcement, privileged-workload restrictions and recovery dependencies. The core VM architecture does not require deploying a container platform just to orchestrate its provisioning. \[[S25](34-appendix-d-sources-and-review-status.md#RA_src_S25); [S26](34-appendix-d-sources-and-review-status.md#RA_src_S26)\]

A new stack joins by implementing the same infrastructure/service interfaces and providing equivalent assurance and lifecycle evidence. It may use different routing, storage or management components. Optional accelerators, high-performance packet processing and special devices remain declared extensions with their constraints on migration, inspection and support. The architecture rejects a required capability gap rather than describing an unsupported approximation as portable.

Boundary of the extension — This chapter defines admission to the architecture, not a complete Kubernetes, bare-metal installer or hardware-driver design. The selected extension needs its own component topology and provisioning profile before it is offered as a production service.

Related engineering: [QUAL §8 — Extensions and release maintenance](../../assurance/site-qualification/8-extensions-and-release-maintenance.md#QUAL_s_008)

PART 4  /  Provisioning strategy

[Previous chapter](18-openstack-hosting-stack-reference-realization.md) · [Chapter index](README.md) · [Next chapter](20-provisioning-model-and-infrastructure-work-packages.md)
