# 17. VMware and NSX hosting-stack reference realization

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:248 BEGIN -->

<a id="__RefHeading___Toc3672_865363315"></a>
<a id="RA_s_017"></a>

<!-- SOURCE-BLOCK RA:248 END -->

<!-- SOURCE-BLOCK RA:249 BEGIN -->

## Component placement

<!-- SOURCE-BLOCK RA:249 END -->

<!-- SOURCE-BLOCK RA:250 BEGIN -->

The VMware pattern uses vCenter-managed ESXi capacity, an explicit networking/security layer such as NSX, and qualified storage and protection services. Plain vSphere networking is not assumed to supply the complete portable security model. NSX distinguishes distributed routing from Edge-hosted service routing. Tier-0/Tier-1 hierarchy and route advertisement affect actual packet paths. Broadcom documents Tier-0 VRF gateways as isolated routing instances under a parent Tier-0. \[[S18](34-appendix-d-sources-and-review-status.md#RA_src_S18); [S33](34-appendix-d-sources-and-review-status.md#RA_src_S33); [S34](34-appendix-d-sources-and-review-status.md#RA_src_S34)\]

<!-- SOURCE-BLOCK RA:250 END -->

<!-- SOURCE-BLOCK RA:251 BEGIN -->

The proposed physical layout separates management workloads, Edge/service capacity and tenant workload pools according to the isolation profile. ESXi transport nodes attach to the platform transport network; Edge nodes have separately controlled uplinks toward the security service and border. vCenter, NSX managers and storage/protection administration use protected management paths. Required host mobility and storage networks remain provider infrastructure.

<!-- SOURCE-BLOCK RA:251 END -->

<!-- SOURCE-BLOCK RA:252 BEGIN -->

![VMware/NSX reference: independent domain routing through the security edge vCenter and NSX management administer ESXi workload pools and Edge capacity. OZ and RZ segments attach to separate Tier-1 gateways and separate upstream Tier-0 VRF or equivalent isolated contexts. No native route leak joins the contexts. Approved domain-to-domain traffic passes through an external logical ZIP. Distributed firewall policy also protects workload endpoints.](../../assets/diagrams/c40f78550c8e0f59dbbc.png)

<!-- SOURCE-BLOCK RA:252 END -->

<!-- SOURCE-BLOCK RA:253 BEGIN -->

<a id="fig_nsx"></a>

Figure 6. VMware/NSX reference: independent domain routing through the security edge

<!-- SOURCE-BLOCK RA:253 END -->

<!-- SOURCE-BLOCK RA:254 BEGIN -->

## Selected routing and enforcement pattern

<!-- SOURCE-BLOCK RA:254 END -->

<!-- SOURCE-BLOCK RA:255 BEGIN -->

The reference assigns a Tier-1 routing context to each independent domain instance and uses an isolated upstream context, such as a supported Tier-0 VRF, to hand it to the provider security edge. Unrestricted native inter-VRF route leaking is not enabled. A shared parent gateway or Edge cluster is a shared resource/failure dependency, not shared routing authorization. Where the selected release cannot provide this pattern, use another qualified isolated upstream design or do not offer that service class.

<!-- SOURCE-BLOCK RA:255 END -->

<!-- SOURCE-BLOCK RA:256 BEGIN -->

This choice deliberately avoids connecting all independent Tier-1 gateways to a common unrestricted Tier-0 table and relying on a downstream firewall. The site design must show the domain prefixes, advertisements, default routes, Edge placement, upstream attachment and return path. It must verify connected and distributed routes as well as centralized service-router policy. A Tier-1 object by itself is not a ZIP, and a conceptual Edge symbol does not prove that every inter-domain packet traverses stateful inspection.

<!-- SOURCE-BLOCK RA:256 END -->

<!-- SOURCE-BLOCK RA:257 BEGIN -->

Mandatory distributed policy handles same-domain microsegmentation and protects endpoints on same-host and cross-host paths. Provider-controlled groups/tags and policy hierarchy prevent tenant rules from expanding mandatory permission. The inter-zone ZIP remains a distinct function with joint domain authority, inspection where required, logging and session-revocation behaviour. A native gateway/distributed ZIP variation needs a complete functional equivalence decision, not just a replacement product name.

<!-- SOURCE-BLOCK RA:257 END -->

<!-- SOURCE-BLOCK RA:258 BEGIN -->


<a id="source-table-258"></a>

| Build responsibility | Commissioned platform resources | Tenant/domain realization |
| --- | --- | --- |
| Compute and storage | vCenter/ESXi pools, eligible hosts, storage policies/backends, images and protection integration | VM placement, virtual hardware, owned disks and protection assignment |
| Virtual networking | NSX control, transport-node configuration, transport zones and Edge capacity | Project/scope as applicable, segments, Tier-1 and isolated upstream associations |
| Security | Provider rule hierarchy, group ownership and security-edge capacity | Endpoint membership, explicit domain boundary and permitted flow rules |
| Management | Protected vCenter/NSX/host/storage administration; credential boundaries | Entitled tenant resource access, not global routing or host administration |
| Automation | vSphere and NSX integration plus edge, name/address and protection services | Several ordered scoped resource changes for one environment |

<!-- SOURCE-BLOCK RA:258 END -->

<!-- SOURCE-BLOCK RA:259 BEGIN -->

<!-- SOURCE-BLOCK RA:259 END -->

<!-- SOURCE-BLOCK RA:260 BEGIN -->

## Provisioning order and failure behaviour

<!-- SOURCE-BLOCK RA:260 END -->

<!-- SOURCE-BLOCK RA:261 BEGIN -->

Commission vCenter/ESXi and storage before offering compute capacity; commission NSX transport and Edge/uplink design before offering tenant networking. The tenant workflow establishes entitled scope, reserves addresses and isolated upstream capacity, creates segments and domain gateways under deny, applies distributed and boundary policy, provisions the VM/storage attachments, and then enables approved service routes and exposure. vSphere and NSX resources are managed as separate technical and authority concerns even when one workflow coordinates them.

<!-- SOURCE-BLOCK RA:261 END -->

<!-- SOURCE-BLOCK RA:262 BEGIN -->

vMotion or equivalent live mobility remains constrained to eligible pools and supported network/storage arrangements. VM restart after host failure must not break co-residency rules. If target capacity is unavailable, the declared service degrades rather than using an ineligible host. Edge failover must preserve the approved session/routing behaviour; active/active or active/standby is a selected, tested mode, not a generic guarantee.

<!-- SOURCE-BLOCK RA:262 END -->

<!-- SOURCE-BLOCK RA:263 BEGIN -->

Acceptance verifies Tier-1/Tier-0 route propagation, no unauthorized inter-VRF path, same-host endpoint enforcement, Edge loss, upstream asymmetry, workload migration, storage/key dependency and restore. Platform and provider release compatibility, gateway feature limits and entitlements are recorded in the implementation profile. The official VRF reference was available as an indexed excerpt during this revision; full-page retrieval was restricted, so this document does not claim a complete review of its release-specific limitations.

<!-- SOURCE-BLOCK RA:263 END -->

<!-- SOURCE-BLOCK RA:264 BEGIN -->

Related engineering: [VND §4 — VMware/NSX: isolated upstream routing and enforcement](../../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md#VND_s_004)

<!-- SOURCE-BLOCK RA:264 END -->

[Previous chapter](16-nutanix-hosting-stack-reference-realization.md) · [Chapter index](README.md) · [Next chapter](18-openstack-hosting-stack-reference-realization.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table](../../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md)

<!-- END GENERATED DECISION LINKS -->
