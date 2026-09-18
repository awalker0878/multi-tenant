# 3. System context and physical hosting topology

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3644_865363315"></a>
<a id="RA_s_003"></a>

A hosting service comprises one or more sites. Each site contains a transport fabric, a protected management environment, shared security and service infrastructure, and one or more hosting cells. A cell provides a bounded pool of vendor-platform capacity. The provider operates these foundations; tenants consume allocated compute, storage, networks and service access within them. A tenant is not a site, a cell or a physical fabric partition.

![Reference hosting topology: common infrastructure with separate vendor realizations External networks connect through provider security edges. Nutanix, VMware and OpenStack hosting cells attach to a common routed transport fabric. Shared service endpoints are separated from their administration. An independent management and OOB plane controls the fabric, edges, services and cells through scoped management paths.](../../assets/diagrams/5220f0cc31c4f54a6e92.png)

<a id="fig_context"></a>

Figure 1. Reference hosting topology: common infrastructure with separate vendor realizations

External networks terminate at provider-controlled border/security interfaces. Workload traffic enters or leaves a domain only through its authorized attachment. The physical fabric supplies transport between platform tunnel endpoints and service attachments; it does not become an implicit inter-tenant router. A platform-local routing boundary therefore remains meaningful even when two cells use the same physical leaf switches.


<a id="source-table-89"></a>

| Infrastructure area | Components and responsibility | Must not imply |
| --- | --- | --- |
| External and security edge | Border handoffs, controlled public/partner access, logical ZIP contexts, ingress and egress | General reachability from an enterprise circuit to every tenant |
| Hosting cells | Compute pools, platform networking, storage integration and platform-local operational services | A shared administrative or routing authority across unrelated tenants |
| Provider services | DNS/time, identity, PKI/KMS, logging, backup, approved image and update services | Workload access to their management interfaces |
| Management foundation | Privileged access, platform managers, infrastructure tooling and recovery access | A workload network carrying privileged administration |
| Physical transport | Redundant IP connectivity, optional fabric EVPN and controlled physical attachments | A universal security-zone VRF taxonomy or a common vendor overlay |

The topology is a functional deployment view, not a cable diagram. Components shown separately have separate authority and interface requirements; physical separation is determined by the adopted isolation profile. A shared edge or shared storage backend must disclose that dependency. The low-level design records the exact power, rack, host, storage, switching and controller failure domains behind every apparently redundant symbol.

Related engineering: [QUAL §2 — Site low-level design and dependency schedule](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)

[Previous chapter](2-design-drivers-and-selected-reference-pattern.md) · [Chapter index](README.md) · [Next chapter](4-hosting-cells-resource-pools-and-failure-boundaries.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0004 — Scale through commissioned hosting cells and capacity pools](../../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md)

<!-- END GENERATED DECISION LINKS -->
