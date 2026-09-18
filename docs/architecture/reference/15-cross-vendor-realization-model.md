# 15. Cross-vendor realization model

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:219 BEGIN -->

<a id="__RefHeading___Toc3668_865363315"></a>
<a id="RA_s_015"></a>

<!-- SOURCE-BLOCK RA:219 END -->

<!-- SOURCE-BLOCK RA:220 BEGIN -->

Worked reference: WD §§3–8 connects the component, tenant address, isolated handoff, forward/return route, service permission and native realization schedules. Its TEST-NET and IPv6 documentation addresses are explanatory values, not actual allocations. Shared-service and temporary-probe resources are counted separately from the four-domain base fixture.

<!-- SOURCE-BLOCK RA:220 END -->

<!-- SOURCE-BLOCK RA:221 BEGIN -->

The reference architecture is stable; its native realization is not identical across products. Each implementation supplies the same tenant isolation, domain routing, zone transitions, resource classes, management separation and lifecycle outcomes. Its compute, network, storage and protection functions may be managed through several APIs. Selecting a hosting platform therefore selects a set of integration responsibilities, not one provider that creates the entire service.

<!-- SOURCE-BLOCK RA:221 END -->

<!-- SOURCE-BLOCK RA:222 BEGIN -->


<a id="source-table-222"></a>

| Architecture component | Nutanix realization | VMware/NSX realization | OpenStack realization |
| --- | --- | --- | --- |
| Platform control | Prism and selected Flow management functions | vCenter and NSX management; associated storage/protection control | Keystone and service control planes; selected distribution tooling |
| Compute pool | AHV cluster/eligible host pool | ESXi cluster/host groups and enforced placement | Nova/Placement with eligible hosts, aggregates and scheduling policy |
| Domain instance | VPC/routing context per approved domain | Tier-1 with isolated upstream routing context in the reference pattern | Neutron network/router context with approved backend and edge attachment |
| Workload segmentation | Qualified Flow security and protected selectors | Distributed policy with provider-owned groups and rule hierarchy | Port security/security groups plus protected mandatory policy boundary |
| Inter-domain ZIP | Isolated external attachment → security-edge context | Isolated Tier-0 VRF/approved equivalent → security-edge context | Isolated external/provider attachment → security-edge context |
| Storage | AOS and qualified block/file/object/protection services | Qualified datastores/storage policies and associated data services | Cinder and selected backend; optional separate file/object services |
| Provisioning | Nutanix APIs/provider plus shared infrastructure integrations | vSphere and NSX APIs/providers plus shared infrastructure integrations | OpenStack APIs/provider plus installer and shared-service integrations |

<!-- SOURCE-BLOCK RA:222 END -->

<!-- SOURCE-BLOCK RA:223 BEGIN -->

<!-- SOURCE-BLOCK RA:223 END -->

<!-- SOURCE-BLOCK RA:224 BEGIN -->

The mappings above are proposed reference realizations, not blanket capability certification. The subsequent chapters identify physical roles, forwarding paths, shared and dedicated resources, and build order. Each site selects the exact supported product, API, hardware and automation versions. A product feature advertised in documentation does not prove its behaviour when combined with the selected backend, licence, policy hierarchy and failure topology.

<!-- SOURCE-BLOCK RA:224 END -->

<!-- SOURCE-BLOCK RA:225 BEGIN -->

## Three different meanings of cross-platform

<!-- SOURCE-BLOCK RA:225 END -->

<!-- SOURCE-BLOCK RA:226 BEGIN -->

Portable deployment means an equivalent environment can be created on another eligible stack from the same hosting requirement. Composite deployment means one approved environment uses resources or services from several stacks at once, with explicit inter-domain connections. Migration means data and workload state are transferred and cut over. These are separate capabilities. Terraform can provision resources for all three, but it does not itself guarantee data conversion, application consistency or live migration between unrelated hypervisors.

<!-- SOURCE-BLOCK RA:226 END -->

<!-- SOURCE-BLOCK RA:227 BEGIN -->

The default is to place a bounded WSD realization in one eligible cell and consume shared services through its controlled interfaces. A split-platform WSD is an explicit variation with a defined reason, latency budget, failure analysis and recovery ownership. Cross-vendor connectivity uses the approved routing/security boundary, not an assumption that the native overlays can be joined directly.

<!-- SOURCE-BLOCK RA:227 END -->

<!-- SOURCE-BLOCK RA:228 BEGIN -->

Mandatory capability gaps cause an explicit rejection or an approved alternative realization. Optional platform extensions remain visible with their portability consequences. The qualification record includes the offered service classes, actual limits, unsupported features, operations coverage and current evidence. It remains separate from the architecture document and from formal system authorization.

<!-- SOURCE-BLOCK RA:228 END -->

<!-- SOURCE-BLOCK RA:229 BEGIN -->

VND §1 defines a single symbolic qualification environment: two tenants, four independent OZ/RZ domain instances, four logical domain attachments, two tenant inter-zone relationships and explicitly scoped services. It is a test fixture, not a production node-count or application-availability design. Each realization must account for additional service, management and redundant physical resources; the logical counts cannot be used as a hardware bill of materials.

<!-- SOURCE-BLOCK RA:229 END -->

<!-- SOURCE-BLOCK RA:230 BEGIN -->

Related engineering: [VND §1 — One reference environment, three native realizations](../../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [VND §6 — Portable, composite and migrated service choices](../../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md#VND_s_006)  •  [VND §7 — Implementation tuple and decision package](../../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md#VND_s_007)

<!-- SOURCE-BLOCK RA:230 END -->

[Previous chapter](14-availability-multi-site-operation-and-recovery-topology.md) · [Chapter index](README.md) · [Next chapter](16-nutanix-hosting-stack-reference-realization.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0005 — Keep vendor overlays local and connect through controlled handoffs](../../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)
- [ADR-0017 — Separate reference adoption, technical qualification and authorization](../../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)

<!-- END GENERATED DECISION LINKS -->
