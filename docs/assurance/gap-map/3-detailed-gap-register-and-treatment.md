# 3. Detailed gap register and treatment

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/01_Gap_Map_and_Decision_Register_v1_4.docx) · [Chapter index](README.md)

> **Source:** GM — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 26dbaac8c13797b58ca5d057f76df8b3da63ec3f4b336036f18f5c6902512207 -->
<!-- SOURCE-BLOCK GM:40 BEGIN -->

<a id="__RefHeading___Toc1263_342027687"></a>
<a id="GM_s_003"></a>

<!-- SOURCE-BLOCK GM:40 END -->

<!-- SOURCE-BLOCK GM:41 BEGIN -->

Parent architecture: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK GM:41 END -->

<!-- SOURCE-BLOCK GM:42 BEGIN -->

The following 34 records identify remaining knowledge/design work in the v1.2 reference scope. Baseline observations are source-derived; proposed treatments are new engineering elaborations in this release. The owner is a required role, not an assigned person. “Specified” means the documentation treatment is present; all implementation/site/vendor/evidence actions below remain open until accepted observations exist.

<!-- SOURCE-BLOCK GM:42 END -->

<!-- SOURCE-BLOCK GM:43 BEGIN -->

<a id="gap_G01"></a>

## G01 — Document hierarchy and precedence

<!-- SOURCE-BLOCK GM:43 END -->

<!-- SOURCE-BLOCK GM:44 BEGIN -->

P0 \| Knowledge organization \| Owner role: Architecture authority \| G0 — design adoption

<!-- SOURCE-BLOCK GM:44 END -->

<!-- SOURCE-BLOCK GM:45 BEGIN -->

Baseline observation: The architecture delegates detail to a site design and traceability package, but no linked engineering document family owns that detail. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§1, 30\]

<!-- SOURCE-BLOCK GM:45 END -->

<!-- SOURCE-BLOCK GM:46 BEGIN -->

Documentation treatment: Introduce one parent architecture, six bounded supplements, stable IDs, reciprocal links and a conflict/change rule.

<!-- SOURCE-BLOCK GM:46 END -->

<!-- SOURCE-BLOCK GM:47 BEGIN -->

Still required: Adopt the document family, owners and repository location. Closure evidence: Approved document register and conflict disposition.

<!-- SOURCE-BLOCK GM:47 END -->

<!-- SOURCE-BLOCK GM:48 BEGIN -->

Trace: [Treatment: GM §1](1-document-family-scope-and-precedence.md#GM_s_001)  •  [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK GM:48 END -->

<!-- SOURCE-BLOCK GM:49 BEGIN -->

<a id="gap_G02"></a>

## G02 — Site and cell independence

<!-- SOURCE-BLOCK GM:49 END -->

<!-- SOURCE-BLOCK GM:50 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Site/platform architect \| G1 — foundation acceptance

<!-- SOURCE-BLOCK GM:50 END -->

<!-- SOURCE-BLOCK GM:51 BEGIN -->

Baseline observation: Cell and failure boundaries are defined, but the evidence needed to substantiate apparently independent resources is not assembled into a site schedule. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§3, 4, 14\]

<!-- SOURCE-BLOCK GM:51 END -->

<!-- SOURCE-BLOCK GM:52 BEGIN -->

Documentation treatment: Supply a dependency worksheet for power, rack, switch, storage, manager, edge and trust services; distinguish reference cell from vendor cluster.

<!-- SOURCE-BLOCK GM:52 END -->

<!-- SOURCE-BLOCK GM:53 BEGIN -->

Still required: Populate actual fault groups and shared dependencies. Closure evidence: As-built dependency map and witnessed failure coverage.

<!-- SOURCE-BLOCK GM:53 END -->

<!-- SOURCE-BLOCK GM:54 BEGIN -->

Trace: [Treatment: QUAL §2](../site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)  •  [RA §3](../../architecture/reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<!-- SOURCE-BLOCK GM:54 END -->

<!-- SOURCE-BLOCK GM:55 BEGIN -->

<a id="gap_G03"></a>

## G03 — Attachment inventory and exhaustion

<!-- SOURCE-BLOCK GM:55 END -->

<!-- SOURCE-BLOCK GM:56 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Network and security-edge engineering \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:56 END -->

<!-- SOURCE-BLOCK GM:57 BEGIN -->

Baseline observation: Isolated attachment slots are required; their allocation unit, lifecycle and scaling arithmetic are not worked through. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§5, 8, 16, 17, 18\]

<!-- SOURCE-BLOCK GM:57 END -->

<!-- SOURCE-BLOCK GM:58 BEGIN -->

Documentation treatment: Define attachment unit, routing/enforcement identity, reservation/reuse sequence and symbolic capacity example.

<!-- SOURCE-BLOCK GM:58 END -->

<!-- SOURCE-BLOCK GM:59 BEGIN -->

Still required: Select supported slot mechanism and measured context limits for each stack. Closure evidence: Four-domain fixture with no shared-path bypass and exhausted-pool rejection.

<!-- SOURCE-BLOCK GM:59 END -->

<!-- SOURCE-BLOCK GM:60 BEGIN -->

Trace: [Treatment: NET §2](../../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)

<!-- SOURCE-BLOCK GM:60 END -->

<!-- SOURCE-BLOCK GM:61 BEGIN -->

<a id="gap_G04"></a>

## G04 — Underlay and overlay ownership

<!-- SOURCE-BLOCK GM:61 END -->

<!-- SOURCE-BLOCK GM:62 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Network engineering \| G1 — foundation acceptance

<!-- SOURCE-BLOCK GM:62 END -->

<!-- SOURCE-BLOCK GM:63 BEGIN -->

Baseline observation: Independent native overlays are selected, but detailed ownership and permitted advertisements still need an interface design. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§5, 15\]

<!-- SOURCE-BLOCK GM:63 END -->

<!-- SOURCE-BLOCK GM:64 BEGIN -->

Documentation treatment: Define separate transport, tenant and service route scopes and allowed/forbidden handoffs.

<!-- SOURCE-BLOCK GM:64 END -->

<!-- SOURCE-BLOCK GM:65 BEGIN -->

Still required: Choose routing model, ASN/prefix allocations and actual border peers. Closure evidence: Approved route schedule and observed RIB/FIB comparison.

<!-- SOURCE-BLOCK GM:65 END -->

<!-- SOURCE-BLOCK GM:66 BEGIN -->

Trace: [Treatment: NET §1](../../engineering/fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)

<!-- SOURCE-BLOCK GM:66 END -->

<!-- SOURCE-BLOCK GM:67 BEGIN -->

<a id="gap_G05"></a>

## G05 — MTU and multihoming budget

<!-- SOURCE-BLOCK GM:67 END -->

<!-- SOURCE-BLOCK GM:68 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Network/platform engineering \| G1 — foundation acceptance

<!-- SOURCE-BLOCK GM:68 END -->

<!-- SOURCE-BLOCK GM:69 BEGIN -->

Baseline observation: The parent requires MTU and fault tests without a worked budget and explicit failure observations. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§5, 10\]

<!-- SOURCE-BLOCK GM:69 END -->

<!-- SOURCE-BLOCK GM:70 BEGIN -->

Documentation treatment: Add per-layer MTU method, declared workload MTU, minimum-path bottleneck and fault cases.

<!-- SOURCE-BLOCK GM:70 END -->

<!-- SOURCE-BLOCK GM:71 BEGIN -->

Still required: Measure NIC/switch/gateway limits and selected encapsulations. Closure evidence: Packet-size and link/peer-failure results for every offered path.

<!-- SOURCE-BLOCK GM:71 END -->

<!-- SOURCE-BLOCK GM:72 BEGIN -->

Trace: [Treatment: NET §5](../../engineering/fabric/5-mtu-performance-and-failure-engineering.md#NET_s_005)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<!-- SOURCE-BLOCK GM:72 END -->

<!-- SOURCE-BLOCK GM:73 BEGIN -->

<a id="gap_G06"></a>

## G06 — Stateful inter-zone path

<!-- SOURCE-BLOCK GM:73 END -->

<!-- SOURCE-BLOCK GM:74 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Security-edge engineering \| G3 — tenant activation

<!-- SOURCE-BLOCK GM:74 END -->

<!-- SOURCE-BLOCK GM:75 BEGIN -->

Baseline observation: The ZIP pattern is clear, but there is no complete forward/return/translation schedule for an example. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§8, 10\]

<!-- SOURCE-BLOCK GM:75 END -->

<!-- SOURCE-BLOCK GM:76 BEGIN -->

Documentation treatment: Provide four-domain route ownership, allowed flow paths, reverse initiation, established sessions and edge-failure handling.

<!-- SOURCE-BLOCK GM:76 END -->

<!-- SOURCE-BLOCK GM:77 BEGIN -->

Still required: Bind routes and inspection to actual native components and HA mode. Closure evidence: Bidirectional path traces, intended denials and failover/session evidence.

<!-- SOURCE-BLOCK GM:77 END -->

<!-- SOURCE-BLOCK GM:78 BEGIN -->

Trace: [Treatment: NET §3](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<!-- SOURCE-BLOCK GM:78 END -->

<!-- SOURCE-BLOCK GM:79 BEGIN -->

<a id="gap_G07"></a>

## G07 — IPv6 service offer

<!-- SOURCE-BLOCK GM:79 END -->

<!-- SOURCE-BLOCK GM:80 BEGIN -->

P1 \| Scope clarification \| Owner role: Network/platform engineering \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:80 END -->

<!-- SOURCE-BLOCK GM:81 BEGIN -->

Baseline observation: Address-family support is conditional, but wording can be read as offering all three modes without a chosen end-to-end capability. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§10, 28\]

<!-- SOURCE-BLOCK GM:81 END -->

<!-- SOURCE-BLOCK GM:82 BEGIN -->

Documentation treatment: Clarify declaration of supported modes and add per-family interface and recovery acceptance.

<!-- SOURCE-BLOCK GM:82 END -->

<!-- SOURCE-BLOCK GM:83 BEGIN -->

Still required: Choose offered modes, service dependencies and local-link controls. Closure evidence: Positive/negative family-specific results; no fabricated IPv4 for IPv6-only.

<!-- SOURCE-BLOCK GM:83 END -->

<!-- SOURCE-BLOCK GM:84 BEGIN -->

Trace: [Treatment: NET §4](../../engineering/fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)

<!-- SOURCE-BLOCK GM:84 END -->

<!-- SOURCE-BLOCK GM:85 BEGIN -->

<a id="gap_G08"></a>

## G08 — DNS protocol completeness

<!-- SOURCE-BLOCK GM:85 END -->

<!-- SOURCE-BLOCK GM:86 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Name/address service owner \| G3 — tenant activation

<!-- SOURCE-BLOCK GM:86 END -->

<!-- SOURCE-BLOCK GM:87 BEGIN -->

Baseline observation: DNS is named as a required service but its protocol set, delegation and fallback are not specified. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§9, 10\]

<!-- SOURCE-BLOCK GM:87 END -->

<!-- SOURCE-BLOCK GM:88 BEGIN -->

Documentation treatment: Add resolver TCP and UDP treatment, DNS ownership, TTL/cutover and negative resolver checks.

<!-- SOURCE-BLOCK GM:88 END -->

<!-- SOURCE-BLOCK GM:89 BEGIN -->

Still required: Choose resolver endpoints, zones, update authority and any encrypted-DNS profile. Closure evidence: UDP, TCP and truncation/fallback checks plus forbidden-resolver denial.

<!-- SOURCE-BLOCK GM:89 END -->

<!-- SOURCE-BLOCK GM:90 BEGIN -->

Trace: [Treatment: SVC §2](../../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)  •  [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<!-- SOURCE-BLOCK GM:90 END -->

<!-- SOURCE-BLOCK GM:91 BEGIN -->

<a id="gap_G09"></a>

## G09 — Management-domain access

<!-- SOURCE-BLOCK GM:91 END -->

<!-- SOURCE-BLOCK GM:92 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Management and identity owners \| G1 — foundation acceptance

<!-- SOURCE-BLOCK GM:92 END -->

<!-- SOURCE-BLOCK GM:93 BEGIN -->

Baseline observation: MZ/OOB separation is explained, but no target-by-target management authority schedule is supplied. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§6, 13\]

<!-- SOURCE-BLOCK GM:93 END -->

<!-- SOURCE-BLOCK GM:94 BEGIN -->

Documentation treatment: Define operator, executor, support, emergency and guest-administration paths with independent revocation and recovery.

<!-- SOURCE-BLOCK GM:94 END -->

<!-- SOURCE-BLOCK GM:95 BEGIN -->

Still required: Assign administrative scopes and surviving OOB dependencies. Closure evidence: Actual role/route review and approved production-path-loss exercise.

<!-- SOURCE-BLOCK GM:95 END -->

<!-- SOURCE-BLOCK GM:96 BEGIN -->

Trace: [Treatment: NET §6](../../engineering/fabric/6-management-paths-and-interface-handover.md#NET_s_006)  •  [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)

<!-- SOURCE-BLOCK GM:96 END -->

<!-- SOURCE-BLOCK GM:97 BEGIN -->

<a id="gap_G10"></a>

## G10 — Sharing and co-residency decisions

<!-- SOURCE-BLOCK GM:97 END -->

<!-- SOURCE-BLOCK GM:98 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Security authority and platform architect \| G0 — design adoption

<!-- SOURCE-BLOCK GM:98 END -->

<!-- SOURCE-BLOCK GM:99 BEGIN -->

Baseline observation: The zone-specific baseline is retained; pool, controller, storage and management sharing must be decided together. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§7, 11, 12\]

<!-- SOURCE-BLOCK GM:99 END -->

<!-- SOURCE-BLOCK GM:100 BEGIN -->

Documentation treatment: Supply a component-level sharing decision record and placement/evacuation constraints for all vendor realizations.

<!-- SOURCE-BLOCK GM:100 END -->

<!-- SOURCE-BLOCK GM:101 BEGIN -->

Still required: Accept zone-authority sharing and HCI controller/storage implications; assess alternatives. Closure evidence: Signed sharing matrix plus placement, migration and restart observations.

<!-- SOURCE-BLOCK GM:101 END -->

<!-- SOURCE-BLOCK GM:102 BEGIN -->

Trace: [Treatment: VND §2](../../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md#VND_s_002)  •  [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)

<!-- SOURCE-BLOCK GM:102 END -->

<!-- SOURCE-BLOCK GM:103 BEGIN -->

<a id="gap_G11"></a>

## G11 — Common complete reference environment

<!-- SOURCE-BLOCK GM:103 END -->

<!-- SOURCE-BLOCK GM:104 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Architecture/platform engineering \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:104 END -->

<!-- SOURCE-BLOCK GM:105 BEGIN -->

Baseline observation: The cross-stack example describes one tenant in prose; native resource and handoff accounting is not fully worked. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§15, 23\]

<!-- SOURCE-BLOCK GM:105 END -->

<!-- SOURCE-BLOCK GM:106 BEGIN -->

Documentation treatment: Define two tenants, four domains, independent attachments and identical expected outcomes across three stacks.

<!-- SOURCE-BLOCK GM:106 END -->

<!-- SOURCE-BLOCK GM:107 BEGIN -->

Still required: Instantiate symbolic resources and select test endpoints in the authorized lab. Closure evidence: Resource/route/service inventory tied to the common fixture.

<!-- SOURCE-BLOCK GM:107 END -->

<!-- SOURCE-BLOCK GM:108 BEGIN -->

Trace: [Treatment: VND §1](../../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)

<!-- SOURCE-BLOCK GM:108 END -->

<!-- SOURCE-BLOCK GM:109 BEGIN -->

<a id="gap_G12"></a>

## G12 — Nutanix realization detail

<!-- SOURCE-BLOCK GM:109 END -->

<!-- SOURCE-BLOCK GM:110 BEGIN -->

P0 \| Vendor validation \| Owner role: Nutanix platform owner \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:110 END -->

<!-- SOURCE-BLOCK GM:111 BEGIN -->

Baseline observation: VPC/no-NAT and Flow design is proposed; actual external attachment, placement and lifecycle limits remain unqualified. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§16\]

<!-- SOURCE-BLOCK GM:111 END -->

<!-- SOURCE-BLOCK GM:112 BEGIN -->

Documentation treatment: Expand installation versus allocation sequence, forwarding, storage path and operation evidence without assuming resource support.

<!-- SOURCE-BLOCK GM:112 END -->

<!-- SOURCE-BLOCK GM:113 BEGIN -->

Still required: Verify installed AOS/Prism/Flow/API/provider/hardware and licence tuple. Closure evidence: Supported-operation matrix, actual handoffs, policy and failure results.

<!-- SOURCE-BLOCK GM:113 END -->

<!-- SOURCE-BLOCK GM:114 BEGIN -->

Trace: [Treatment: VND §3](../../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md#VND_s_003)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)

<!-- SOURCE-BLOCK GM:114 END -->

<!-- SOURCE-BLOCK GM:115 BEGIN -->

<a id="gap_G13"></a>

## G13 — VMware/NSX upstream realization

<!-- SOURCE-BLOCK GM:115 END -->

<!-- SOURCE-BLOCK GM:116 BEGIN -->

P0 \| Vendor validation \| Owner role: VMware/NSX platform owner \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:116 END -->

<!-- SOURCE-BLOCK GM:117 BEGIN -->

Baseline observation: Tier-0 VRF or equivalent is proposed; full source retrieval was restricted and no exact supported tuple is selected. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§17\]

<!-- SOURCE-BLOCK GM:117 END -->

<!-- SOURCE-BLOCK GM:118 BEGIN -->

Documentation treatment: Retain explicit source limitation; define isolated routing invariants, acceptance alternatives and required vendor confirmation.

<!-- SOURCE-BLOCK GM:118 END -->

<!-- SOURCE-BLOCK GM:119 BEGIN -->

Still required: Confirm gateway/VRF/Edge features, limits, entitlements and provider operation coverage. Closure evidence: Current vendor-backed low-level design plus route-propagation and Edge-failure tests.

<!-- SOURCE-BLOCK GM:119 END -->

<!-- SOURCE-BLOCK GM:120 BEGIN -->

Trace: [Treatment: VND §4](../../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md#VND_s_004)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)

<!-- SOURCE-BLOCK GM:120 END -->

<!-- SOURCE-BLOCK GM:121 BEGIN -->

<a id="gap_G14"></a>

## G14 — OpenStack mandatory policy

<!-- SOURCE-BLOCK GM:121 END -->

<!-- SOURCE-BLOCK GM:122 BEGIN -->

P0 \| Vendor validation \| Owner role: OpenStack platform owner \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:122 END -->

<!-- SOURCE-BLOCK GM:123 BEGIN -->

Baseline observation: ML2/OVN reference and editable security groups are discussed, but provider-owned policy realization needs a specific design. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§18\]

<!-- SOURCE-BLOCK GM:123 END -->

<!-- SOURCE-BLOCK GM:124 BEGIN -->

Documentation treatment: Separate Neutron authority, mandatory control, tenant permits and backend ownership; enumerate alternate attachment paths.

<!-- SOURCE-BLOCK GM:124 END -->

<!-- SOURCE-BLOCK GM:125 BEGIN -->

Still required: Select distribution/backend/API policy and persistent mandatory enforcement mechanism. Closure evidence: Default-policy, port authority, relocation, gateway and volume-isolation results.

<!-- SOURCE-BLOCK GM:125 END -->

<!-- SOURCE-BLOCK GM:126 BEGIN -->

Trace: [Treatment: VND §5](../../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md#VND_s_005)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)

<!-- SOURCE-BLOCK GM:126 END -->

<!-- SOURCE-BLOCK GM:127 BEGIN -->

<a id="gap_G15"></a>

## G15 — Cross-stack communication versus migration

<!-- SOURCE-BLOCK GM:127 END -->

<!-- SOURCE-BLOCK GM:128 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Architecture and migration owners \| G0 — design adoption

<!-- SOURCE-BLOCK GM:128 END -->

<!-- SOURCE-BLOCK GM:129 BEGIN -->

Baseline observation: Portable, composite and migrated are distinguished; acceptance criteria for choosing among them are not tabulated. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§15, 27\]

<!-- SOURCE-BLOCK GM:129 END -->

<!-- SOURCE-BLOCK GM:130 BEGIN -->

Documentation treatment: Add deployment-mode decisions, cross-stack service boundaries and unsupported live-migration handling.

<!-- SOURCE-BLOCK GM:130 END -->

<!-- SOURCE-BLOCK GM:131 BEGIN -->

Still required: Choose the required capability and data movement/consistency method. Closure evidence: Approved mode, dependency budget and target recovery evidence.

<!-- SOURCE-BLOCK GM:131 END -->

<!-- SOURCE-BLOCK GM:132 BEGIN -->

Trace: [Treatment: VND §6](../../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md#VND_s_006)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<!-- SOURCE-BLOCK GM:132 END -->

<!-- SOURCE-BLOCK GM:133 BEGIN -->

<a id="gap_G16"></a>

## G16 — Work-package handoffs

<!-- SOURCE-BLOCK GM:133 END -->

<!-- SOURCE-BLOCK GM:134 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Provisioning/service owners \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:134 END -->

<!-- SOURCE-BLOCK GM:135 BEGIN -->

Baseline observation: P0–P6 are defined, but there is no minimum handoff record for each owner. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§20, 22, 24\]

<!-- SOURCE-BLOCK GM:135 END -->

<!-- SOURCE-BLOCK GM:136 BEGIN -->

Documentation treatment: Define accepted inputs, actual owned outputs, release conditions, downstream consumers and resource-safe reversal.

<!-- SOURCE-BLOCK GM:136 END -->

<!-- SOURCE-BLOCK GM:137 BEGIN -->

Still required: Bind packages to selected tools, identities and operating owners. Closure evidence: Each dependency has an accepted handoff; no borrowed broad credentials.

<!-- SOURCE-BLOCK GM:137 END -->

<!-- SOURCE-BLOCK GM:138 BEGIN -->

Trace: [Treatment: PROV §1](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)  •  [RA §20](../../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK GM:138 END -->

<!-- SOURCE-BLOCK GM:139 BEGIN -->

<a id="gap_G17"></a>

## G17 — Independent Day-0 bootstrap

<!-- SOURCE-BLOCK GM:139 END -->

<!-- SOURCE-BLOCK GM:140 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Foundation/management owner \| G1 — foundation acceptance

<!-- SOURCE-BLOCK GM:140 END -->

<!-- SOURCE-BLOCK GM:141 BEGIN -->

Baseline observation: Bootstrap order is specified, but an explicit minimum surviving service set and transition record is absent. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§21, 13, 14\]

<!-- SOURCE-BLOCK GM:141 END -->

<!-- SOURCE-BLOCK GM:142 BEGIN -->

Documentation treatment: Provide bootstrap dependency cuts, temporary authority, steady-state transfer and recovery custody.

<!-- SOURCE-BLOCK GM:142 END -->

<!-- SOURCE-BLOCK GM:143 BEGIN -->

Still required: Choose independent console, trust, name/time, artifact and state recovery locations. Closure evidence: Recovery from primary platform unavailability and revoked temporary access.

<!-- SOURCE-BLOCK GM:143 END -->

<!-- SOURCE-BLOCK GM:144 BEGIN -->

Trace: [Treatment: PROV §2](../../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md#PROV_s_002)  •  [RA §21](../../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md#RA_s_021)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<!-- SOURCE-BLOCK GM:144 END -->

<!-- SOURCE-BLOCK GM:145 BEGIN -->

<a id="gap_G18"></a>

## G18 — Operation-level tool coverage

<!-- SOURCE-BLOCK GM:145 END -->

<!-- SOURCE-BLOCK GM:146 BEGIN -->

P0 \| Implementation coverage \| Owner role: Platform and automation engineering \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:146 END -->

<!-- SOURCE-BLOCK GM:147 BEGIN -->

Baseline observation: Provider coverage must be checked per operation; the reusable inventory to make that decision is not supplied. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§22, 24\]

<!-- SOURCE-BLOCK GM:147 END -->

<!-- SOURCE-BLOCK GM:148 BEGIN -->

Documentation treatment: Add resource-operation matrix with observe/create/update/adopt/replace/delete/recover status and supported alternatives.

<!-- SOURCE-BLOCK GM:148 END -->

<!-- SOURCE-BLOCK GM:149 BEGIN -->

Still required: Populate exact resources and support evidence; implement missing owned integrations. Closure evidence: Witnessed lifecycle and failure reconciliation, not a provider-name checkbox.

<!-- SOURCE-BLOCK GM:149 END -->

<!-- SOURCE-BLOCK GM:150 BEGIN -->

Trace: [Treatment: PROV §3](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK GM:150 END -->

<!-- SOURCE-BLOCK GM:151 BEGIN -->

<a id="gap_G19"></a>

## G19 — Activation and rollback safety

<!-- SOURCE-BLOCK GM:151 END -->

<!-- SOURCE-BLOCK GM:152 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Provisioning and security-edge owners \| G3 — tenant activation

<!-- SOURCE-BLOCK GM:152 END -->

<!-- SOURCE-BLOCK GM:153 BEGIN -->

Baseline observation: Internal verification and post-activation checks exist; detailed irreversible boundaries and safe responses need elaboration. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§23, 24\]

<!-- SOURCE-BLOCK GM:153 END -->

<!-- SOURCE-BLOCK GM:154 BEGIN -->

Documentation treatment: Define deny-first assembly, canary/controlled activation, session withdrawal and preservation of newly written data.

<!-- SOURCE-BLOCK GM:154 END -->

<!-- SOURCE-BLOCK GM:155 BEGIN -->

Still required: Implement actual activation gates and data-safe recovery actions. Closure evidence: Interrupted-stage and failed-live-check exercises preserve unrelated services.

<!-- SOURCE-BLOCK GM:155 END -->

<!-- SOURCE-BLOCK GM:156 BEGIN -->

Trace: [Treatment: PROV §4](../../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md#PROV_s_004)  •  [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK GM:156 END -->

<!-- SOURCE-BLOCK GM:157 BEGIN -->

<a id="gap_G20"></a>

## G20 — Single-writer and stale executor

<!-- SOURCE-BLOCK GM:157 END -->

<!-- SOURCE-BLOCK GM:158 BEGIN -->

P1 \| Implementation coverage \| Owner role: Automation/platform owners \| G3 — tenant activation

<!-- SOURCE-BLOCK GM:158 END -->

<!-- SOURCE-BLOCK GM:159 BEGIN -->

Baseline observation: Single ownership and stale plan checks are required; delayed native operations after executor failure are not developed. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§24, 25\]

<!-- SOURCE-BLOCK GM:159 END -->

<!-- SOURCE-BLOCK GM:160 BEGIN -->

Documentation treatment: Add ownership transfer, stop-and-discover procedure, outstanding task checks and conditional resumption.

<!-- SOURCE-BLOCK GM:160 END -->

<!-- SOURCE-BLOCK GM:161 BEGIN -->

Still required: Qualify locking, credential revocation and task discovery for every executor. Closure evidence: No concurrent competing writers or duplicate allocation after timeout.

<!-- SOURCE-BLOCK GM:161 END -->

<!-- SOURCE-BLOCK GM:162 BEGIN -->

Trace: [Treatment: PROV §5](../../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md#PROV_s_005)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)  •  [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)

<!-- SOURCE-BLOCK GM:162 END -->

<!-- SOURCE-BLOCK GM:163 BEGIN -->

<a id="gap_G21"></a>

## G21 — Brownfield adoption sequence

<!-- SOURCE-BLOCK GM:163 END -->

<!-- SOURCE-BLOCK GM:164 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Existing service and platform owners \| G3 — tenant activation

<!-- SOURCE-BLOCK GM:164 END -->

<!-- SOURCE-BLOCK GM:165 BEGIN -->

Baseline observation: Discovery and reviewed adoption are stated, but a complete no-replacement acceptance sequence is not shown. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§25\]

<!-- SOURCE-BLOCK GM:165 END -->

<!-- SOURCE-BLOCK GM:166 BEGIN -->

Documentation treatment: Provide discovery, ownership freeze, supported import, no-op plan and canary change gates.

<!-- SOURCE-BLOCK GM:166 END -->

<!-- SOURCE-BLOCK GM:167 BEGIN -->

Still required: Inventory live resources and settle existing management ownership. Closure evidence: Reviewed non-destructive plan, rollback boundary and service checks.

<!-- SOURCE-BLOCK GM:167 END -->

<!-- SOURCE-BLOCK GM:168 BEGIN -->

Trace: [Treatment: PROV §6](../../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md#PROV_s_006)  •  [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)

<!-- SOURCE-BLOCK GM:168 END -->

<!-- SOURCE-BLOCK GM:169 BEGIN -->

<a id="gap_G22"></a>

## G22 — Shared-service dependency placement

<!-- SOURCE-BLOCK GM:169 END -->

<!-- SOURCE-BLOCK GM:170 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Shared-service architects \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:170 END -->

<!-- SOURCE-BLOCK GM:171 BEGIN -->

Baseline observation: Consumption/administration are distinct; provider service placement and dependency failure are not mapped service by service. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§9, 13, 22\]

<!-- SOURCE-BLOCK GM:171 END -->

<!-- SOURCE-BLOCK GM:172 BEGIN -->

Documentation treatment: Add endpoint/management/backend/dependency schedules and distinguish shared endpoints from independent service instances.

<!-- SOURCE-BLOCK GM:172 END -->

<!-- SOURCE-BLOCK GM:173 BEGIN -->

Still required: Choose placements, tenancy controls and actual service dependencies. Closure evidence: Service consumption and administrative-denial tests in failure conditions.

<!-- SOURCE-BLOCK GM:173 END -->

<!-- SOURCE-BLOCK GM:174 BEGIN -->

Trace: [Treatment: SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)

<!-- SOURCE-BLOCK GM:174 END -->

<!-- SOURCE-BLOCK GM:175 BEGIN -->

<a id="gap_G23"></a>

## G23 — Key and certificate recovery

<!-- SOURCE-BLOCK GM:175 END -->

<!-- SOURCE-BLOCK GM:176 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Identity, PKI and key owners \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:176 END -->

<!-- SOURCE-BLOCK GM:177 BEGIN -->

Baseline observation: Independent custody and no plaintext fallback are required; recovery key lifetime, trust renewal and scope are not worked. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§13, 14\]

<!-- SOURCE-BLOCK GM:177 END -->

<!-- SOURCE-BLOCK GM:178 BEGIN -->

Documentation treatment: Add separate key-use/admin/recovery/disposal paths and retained-copy dependency ledger.

<!-- SOURCE-BLOCK GM:178 END -->

<!-- SOURCE-BLOCK GM:179 BEGIN -->

Still required: Select approved protocols/module evidence, custody and recovery process. Closure evidence: Rotation, revocation and outage/restore results with retained-data recovery.

<!-- SOURCE-BLOCK GM:179 END -->

<!-- SOURCE-BLOCK GM:180 BEGIN -->

Trace: [Treatment: SVC §3](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<!-- SOURCE-BLOCK GM:180 END -->

<!-- SOURCE-BLOCK GM:181 BEGIN -->

<a id="gap_G24"></a>

## G24 — Storage copy and attachment lineage

<!-- SOURCE-BLOCK GM:181 END -->

<!-- SOURCE-BLOCK GM:182 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Storage and data owners \| G3 — tenant activation

<!-- SOURCE-BLOCK GM:182 END -->

<!-- SOURCE-BLOCK GM:183 BEGIN -->

Baseline observation: Storage paths and retained copies are described but no filled copy lineage or attachment lifecycle is supplied. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§12, 27\]

<!-- SOURCE-BLOCK GM:183 END -->

<!-- SOURCE-BLOCK GM:184 BEGIN -->

Documentation treatment: Add authoritative copy/attachment records, data access paths, inherited category and disposal checkpoints.

<!-- SOURCE-BLOCK GM:184 END -->

<!-- SOURCE-BLOCK GM:185 BEGIN -->

Still required: Map real backend, image, snapshot, clone, replica and backup mechanisms. Closure evidence: Foreign attachment/export denials and retained-copy disposal accounting.

<!-- SOURCE-BLOCK GM:185 END -->

<!-- SOURCE-BLOCK GM:186 BEGIN -->

Trace: [Treatment: SVC §4](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<!-- SOURCE-BLOCK GM:186 END -->

<!-- SOURCE-BLOCK GM:187 BEGIN -->

<a id="gap_G25"></a>

## G25 — Backup and isolated restore

<!-- SOURCE-BLOCK GM:187 END -->

<!-- SOURCE-BLOCK GM:188 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Backup and recovery owners \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:188 END -->

<!-- SOURCE-BLOCK GM:189 BEGIN -->

Baseline observation: Restore is the acceptance metric; proxy/API/data paths and reconstruction dependencies need more detail. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§12, 14, 27\]

<!-- SOURCE-BLOCK GM:189 END -->

<!-- SOURCE-BLOCK GM:190 BEGIN -->

Documentation treatment: Provide capture/transfer/repository separation and stepwise isolated restore with key/catalogue prerequisites.

<!-- SOURCE-BLOCK GM:190 END -->

<!-- SOURCE-BLOCK GM:191 BEGIN -->

Still required: Choose supported capture/consistency methods and approve RTO/RPO and retention. Closure evidence: Recover useful test data and demonstrate isolation before reconnecting.

<!-- SOURCE-BLOCK GM:191 END -->

<!-- SOURCE-BLOCK GM:192 BEGIN -->

Trace: [Treatment: SVC §5](../../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md#SVC_s_005)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<!-- SOURCE-BLOCK GM:192 END -->

<!-- SOURCE-BLOCK GM:193 BEGIN -->

<a id="gap_G26"></a>

## G26 — Site-loss and failback ownership

<!-- SOURCE-BLOCK GM:193 END -->

<!-- SOURCE-BLOCK GM:194 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Continuity and data owners \| G4 — recovery/operational acceptance

<!-- SOURCE-BLOCK GM:194 END -->

<!-- SOURCE-BLOCK GM:195 BEGIN -->

Baseline observation: Fencing and failback are required; partition, alternate writer and reverse synchronization decisions are not tabulated. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§14, 27\]

<!-- SOURCE-BLOCK GM:195 END -->

<!-- SOURCE-BLOCK GM:196 BEGIN -->

Documentation treatment: Define failure/authority matrix, writer exclusion, activation and return-to-primary sequence.

<!-- SOURCE-BLOCK GM:196 END -->

<!-- SOURCE-BLOCK GM:197 BEGIN -->

Still required: Populate surviving dependencies and specific fencing/consistency method. Closure evidence: Observed site/partition recovery with measured objectives and safe failback.

<!-- SOURCE-BLOCK GM:197 END -->

<!-- SOURCE-BLOCK GM:198 BEGIN -->

Trace: [Treatment: SVC §6](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<!-- SOURCE-BLOCK GM:198 END -->

<!-- SOURCE-BLOCK GM:199 BEGIN -->

<a id="gap_G27"></a>

## G27 — Measured capacity and admission

<!-- SOURCE-BLOCK GM:199 END -->

<!-- SOURCE-BLOCK GM:200 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Capacity and platform owners \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:200 END -->

<!-- SOURCE-BLOCK GM:201 BEGIN -->

Baseline observation: Capacity principle is present; no worked multi-resource admission or edge-context accounting example exists. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§4, 14, 26\]

<!-- SOURCE-BLOCK GM:201 END -->

<!-- SOURCE-BLOCK GM:202 BEGIN -->

Documentation treatment: Add unit-aware resource ledger and illustrative surviving-capacity calculations; distinguish reservations from observed use.

<!-- SOURCE-BLOCK GM:202 END -->

<!-- SOURCE-BLOCK GM:203 BEGIN -->

Still required: Measure capacity under agreed failure/maintenance and security feature load. Closure evidence: Approved service envelope with binding bottleneck and growth trigger.

<!-- SOURCE-BLOCK GM:203 END -->

<!-- SOURCE-BLOCK GM:204 BEGIN -->

Trace: [Treatment: QUAL §3](../site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)

<!-- SOURCE-BLOCK GM:204 END -->

<!-- SOURCE-BLOCK GM:205 BEGIN -->

<a id="gap_G28"></a>

## G28 — Service objectives and retention parameters

<!-- SOURCE-BLOCK GM:205 END -->

<!-- SOURCE-BLOCK GM:206 BEGIN -->

P0 \| Site/service decision \| Owner role: Service/data owners \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:206 END -->

<!-- SOURCE-BLOCK GM:207 BEGIN -->

Baseline observation: Actual SLO/RTO/RPO and retention remain implementation responsibilities. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§12, 14, 26\]

<!-- SOURCE-BLOCK GM:207 END -->

<!-- SOURCE-BLOCK GM:208 BEGIN -->

Documentation treatment: Provide a parameter decision sheet with measurement scope, approving role, feasibility proof and dependencies.

<!-- SOURCE-BLOCK GM:208 END -->

<!-- SOURCE-BLOCK GM:209 BEGIN -->

Still required: Supply business requirements, retention obligations and measured feasibility. Closure evidence: Approved values and test method; no unspecified production promise.

<!-- SOURCE-BLOCK GM:209 END -->

<!-- SOURCE-BLOCK GM:210 BEGIN -->

Trace: [Treatment: QUAL §4](../site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)

<!-- SOURCE-BLOCK GM:210 END -->

<!-- SOURCE-BLOCK GM:211 BEGIN -->

<a id="gap_G29"></a>

## G29 — Qualification applicability and sequencing

<!-- SOURCE-BLOCK GM:211 END -->

<!-- SOURCE-BLOCK GM:212 BEGIN -->

P0 \| Qualification evidence \| Owner role: Assurance engineering \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:212 END -->

<!-- SOURCE-BLOCK GM:213 BEGIN -->

Baseline observation: 80 inherited tests and 12 addenda remain not-run; not every test applies at every gate. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§28, 30\]

<!-- SOURCE-BLOCK GM:213 END -->

<!-- SOURCE-BLOCK GM:214 BEGIN -->

Documentation treatment: Separate first-stack qualification from second-stack portability and use assertion-level applicability with explicit not-applicable authority.

<!-- SOURCE-BLOCK GM:214 END -->

<!-- SOURCE-BLOCK GM:215 BEGIN -->

Still required: Select applicable procedures and execute on the actual tuple. Closure evidence: All mandatory observations supported; blocked/not-run never count as pass.

<!-- SOURCE-BLOCK GM:215 END -->

<!-- SOURCE-BLOCK GM:216 BEGIN -->

Trace: [Treatment: QUAL §5](../site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK GM:216 END -->

<!-- SOURCE-BLOCK GM:217 BEGIN -->

<a id="gap_G30"></a>

## G30 — Control inheritance and external dependencies

<!-- SOURCE-BLOCK GM:217 END -->

<!-- SOURCE-BLOCK GM:218 BEGIN -->

P0 \| Engineering elaboration \| Owner role: Security authority and service owners \| G0 — design adoption

<!-- SOURCE-BLOCK GM:218 END -->

<!-- SOURCE-BLOCK GM:219 BEGIN -->

Baseline observation: Applicable controls and responsibility are required; organizational/physical control inheritance is not assembled. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§1, 26, 28\]

<!-- SOURCE-BLOCK GM:219 END -->

<!-- SOURCE-BLOCK GM:220 BEGIN -->

Documentation treatment: Add provider/tenant/shared/inherited dispositions including physical, personnel, maintenance and training interfaces.

<!-- SOURCE-BLOCK GM:220 END -->

<!-- SOURCE-BLOCK GM:221 BEGIN -->

Still required: Select actual catalogue controls/parameters and accept inherited evidence. Closure evidence: Control allocation, residual gaps and formal decision references.

<!-- SOURCE-BLOCK GM:221 END -->

<!-- SOURCE-BLOCK GM:222 BEGIN -->

Trace: [Treatment: QUAL §6](../site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md#QUAL_s_006)  •  [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)

<!-- SOURCE-BLOCK GM:222 END -->

<!-- SOURCE-BLOCK GM:223 BEGIN -->

<a id="gap_G31"></a>

## G31 — Operating ownership and incident behaviour

<!-- SOURCE-BLOCK GM:223 END -->

<!-- SOURCE-BLOCK GM:224 BEGIN -->

P1 \| Engineering elaboration \| Owner role: Operations/service management \| G4 — recovery/operational acceptance

<!-- SOURCE-BLOCK GM:224 END -->

<!-- SOURCE-BLOCK GM:225 BEGIN -->

Baseline observation: Roles are described in prose; a decision-level accountability and handover schedule is absent. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§25, 26, 27\]

<!-- SOURCE-BLOCK GM:225 END -->

<!-- SOURCE-BLOCK GM:226 BEGIN -->

Documentation treatment: Add accountable decision owner matrix, containment precedence, monitoring questions and handover acceptance.

<!-- SOURCE-BLOCK GM:226 END -->

<!-- SOURCE-BLOCK GM:227 BEGIN -->

Still required: Name teams/on-call owners and integrate local incident/change processes. Closure evidence: Accepted handover, credential review and scoped incident exercise.

<!-- SOURCE-BLOCK GM:227 END -->

<!-- SOURCE-BLOCK GM:228 BEGIN -->

Trace: [Treatment: QUAL §7](../site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)  •  [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<!-- SOURCE-BLOCK GM:228 END -->

<!-- SOURCE-BLOCK GM:229 BEGIN -->

<a id="gap_G32"></a>

## G32 — Version and source provenance

<!-- SOURCE-BLOCK GM:229 END -->

<!-- SOURCE-BLOCK GM:230 BEGIN -->

P1 \| Vendor validation \| Owner role: Platform engineering and architecture \| G2 — platform/service acceptance

<!-- SOURCE-BLOCK GM:230 END -->

<!-- SOURCE-BLOCK GM:231 BEGIN -->

Baseline observation: Some references are historic, inherited or access-limited; no source review state should be mistaken for qualification. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§15, 16, 17, 18, 24\]

<!-- SOURCE-BLOCK GM:231 END -->

<!-- SOURCE-BLOCK GM:232 BEGIN -->

Documentation treatment: Record review status separately from source edition; require exact installed tuple and supported-operation evidence.

<!-- SOURCE-BLOCK GM:232 END -->

<!-- SOURCE-BLOCK GM:233 BEGIN -->

Still required: Obtain unavailable current vendor material and select installed versions. Closure evidence: Dated compatibility record and qualified lifecycle results.

<!-- SOURCE-BLOCK GM:233 END -->

<!-- SOURCE-BLOCK GM:234 BEGIN -->

Trace: [Treatment: VND §7](../../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md#VND_s_007)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK GM:234 END -->

<!-- SOURCE-BLOCK GM:235 BEGIN -->

<a id="gap_G33"></a>

## G33 — Bounded extensions

<!-- SOURCE-BLOCK GM:235 END -->

<!-- SOURCE-BLOCK GM:236 BEGIN -->

P2 \| Scope boundary \| Owner role: Extension service owner \| G0 — extension adoption

<!-- SOURCE-BLOCK GM:236 END -->

<!-- SOURCE-BLOCK GM:237 BEGIN -->

Baseline observation: Bare metal and containers are explicitly extensions, not complete implementations. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§19\]

<!-- SOURCE-BLOCK GM:237 END -->

<!-- SOURCE-BLOCK GM:238 BEGIN -->

Documentation treatment: Keep them outside the base offered service until dedicated topology, ownership and recovery qualification exists.

<!-- SOURCE-BLOCK GM:238 END -->

<!-- SOURCE-BLOCK GM:239 BEGIN -->

Still required: Develop extension-specific low-level design only when requested as a service. Closure evidence: Approved scope and complete applicable extension qualification.

<!-- SOURCE-BLOCK GM:239 END -->

<!-- SOURCE-BLOCK GM:240 BEGIN -->

Trace: [Treatment: QUAL §8](../site-qualification/8-extensions-and-release-maintenance.md#QUAL_s_008)  •  [RA §19](../../architecture/reference/19-physical-workloads-and-future-platform-extensions.md#RA_s_019)

<!-- SOURCE-BLOCK GM:240 END -->

<!-- SOURCE-BLOCK GM:241 BEGIN -->

<a id="gap_G34"></a>

## G34 — Knowledge maintenance and cross-link integrity

<!-- SOURCE-BLOCK GM:241 END -->

<!-- SOURCE-BLOCK GM:242 BEGIN -->

P2 \| Knowledge organization \| Owner role: Architecture document owner \| G0 — design adoption

<!-- SOURCE-BLOCK GM:242 END -->

<!-- SOURCE-BLOCK GM:243 BEGIN -->

Baseline observation: A growing document set can duplicate policy or allow supplement drift. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§1, 30\]

<!-- SOURCE-BLOCK GM:243 END -->

<!-- SOURCE-BLOCK GM:244 BEGIN -->

Documentation treatment: Assign a primary home per topic, stable parent anchors and a release-wide link/requirement mapping check.

<!-- SOURCE-BLOCK GM:244 END -->

<!-- SOURCE-BLOCK GM:245 BEGIN -->

Still required: Assign maintaining owners and release cadence. Closure evidence: Consistent version set, validated links and approved change record.

<!-- SOURCE-BLOCK GM:245 END -->

<!-- SOURCE-BLOCK GM:246 BEGIN -->

Trace: [Treatment: GM §2](2-primary-knowledge-homes-and-cross-cutting-changes.md#GM_s_002)  •  [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK GM:246 END -->

[Previous chapter](2-primary-knowledge-homes-and-cross-cutting-changes.md) · [Chapter index](README.md) · [Next chapter](4-open-decision-package-for-implementation.md)
