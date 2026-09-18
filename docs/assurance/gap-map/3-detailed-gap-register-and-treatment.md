# 3. Detailed gap register and treatment

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/01_Gap_Map_and_Decision_Register_v1_4.docx) · [Chapter index](README.md)

> **Source:** GM — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 26dbaac8c13797b58ca5d057f76df8b3da63ec3f4b336036f18f5c6902512207 -->
<a id="__RefHeading___Toc1263_342027687"></a>
<a id="GM_s_003"></a>

Parent architecture: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

The following 34 records identify remaining knowledge/design work in the v1.2 reference scope. Baseline observations are source-derived; proposed treatments are new engineering elaborations in this release. The owner is a required role, not an assigned person. “Specified” means the documentation treatment is present; all implementation/site/vendor/evidence actions below remain open until accepted observations exist.

<a id="gap_G01"></a>

## G01 — Document hierarchy and precedence

P0 \| Knowledge organization \| Owner role: Architecture authority \| G0 — design adoption

Baseline observation: The architecture delegates detail to a site design and traceability package, but no linked engineering document family owns that detail. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§1, 30\]

Documentation treatment: Introduce one parent architecture, six bounded supplements, stable IDs, reciprocal links and a conflict/change rule.

Still required: Adopt the document family, owners and repository location. Closure evidence: Approved document register and conflict disposition.

Trace: [Treatment: GM §1](1-document-family-scope-and-precedence.md#GM_s_001)  •  [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<a id="gap_G02"></a>

## G02 — Site and cell independence

P0 \| Engineering elaboration \| Owner role: Site/platform architect \| G1 — foundation acceptance

Baseline observation: Cell and failure boundaries are defined, but the evidence needed to substantiate apparently independent resources is not assembled into a site schedule. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§3, 4, 14\]

Documentation treatment: Supply a dependency worksheet for power, rack, switch, storage, manager, edge and trust services; distinguish reference cell from vendor cluster.

Still required: Populate actual fault groups and shared dependencies. Closure evidence: As-built dependency map and witnessed failure coverage.

Trace: [Treatment: QUAL §2](../site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)  •  [RA §3](../../architecture/reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<a id="gap_G03"></a>

## G03 — Attachment inventory and exhaustion

P0 \| Engineering elaboration \| Owner role: Network and security-edge engineering \| G2 — platform/service acceptance

Baseline observation: Isolated attachment slots are required; their allocation unit, lifecycle and scaling arithmetic are not worked through. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§5, 8, 16, 17, 18\]

Documentation treatment: Define attachment unit, routing/enforcement identity, reservation/reuse sequence and symbolic capacity example.

Still required: Select supported slot mechanism and measured context limits for each stack. Closure evidence: Four-domain fixture with no shared-path bypass and exhausted-pool rejection.

Trace: [Treatment: NET §2](../../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)

<a id="gap_G04"></a>

## G04 — Underlay and overlay ownership

P1 \| Engineering elaboration \| Owner role: Network engineering \| G1 — foundation acceptance

Baseline observation: Independent native overlays are selected, but detailed ownership and permitted advertisements still need an interface design. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§5, 15\]

Documentation treatment: Define separate transport, tenant and service route scopes and allowed/forbidden handoffs.

Still required: Choose routing model, ASN/prefix allocations and actual border peers. Closure evidence: Approved route schedule and observed RIB/FIB comparison.

Trace: [Treatment: NET §1](../../engineering/fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)

<a id="gap_G05"></a>

## G05 — MTU and multihoming budget

P1 \| Engineering elaboration \| Owner role: Network/platform engineering \| G1 — foundation acceptance

Baseline observation: The parent requires MTU and fault tests without a worked budget and explicit failure observations. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§5, 10\]

Documentation treatment: Add per-layer MTU method, declared workload MTU, minimum-path bottleneck and fault cases.

Still required: Measure NIC/switch/gateway limits and selected encapsulations. Closure evidence: Packet-size and link/peer-failure results for every offered path.

Trace: [Treatment: NET §5](../../engineering/fabric/5-mtu-performance-and-failure-engineering.md#NET_s_005)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<a id="gap_G06"></a>

## G06 — Stateful inter-zone path

P0 \| Engineering elaboration \| Owner role: Security-edge engineering \| G3 — tenant activation

Baseline observation: The ZIP pattern is clear, but there is no complete forward/return/translation schedule for an example. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§8, 10\]

Documentation treatment: Provide four-domain route ownership, allowed flow paths, reverse initiation, established sessions and edge-failure handling.

Still required: Bind routes and inspection to actual native components and HA mode. Closure evidence: Bidirectional path traces, intended denials and failover/session evidence.

Trace: [Treatment: NET §3](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<a id="gap_G07"></a>

## G07 — IPv6 service offer

P1 \| Scope clarification \| Owner role: Network/platform engineering \| G2 — platform/service acceptance

Baseline observation: Address-family support is conditional, but wording can be read as offering all three modes without a chosen end-to-end capability. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§10, 28\]

Documentation treatment: Clarify declaration of supported modes and add per-family interface and recovery acceptance.

Still required: Choose offered modes, service dependencies and local-link controls. Closure evidence: Positive/negative family-specific results; no fabricated IPv4 for IPv6-only.

Trace: [Treatment: NET §4](../../engineering/fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)

<a id="gap_G08"></a>

## G08 — DNS protocol completeness

P0 \| Engineering elaboration \| Owner role: Name/address service owner \| G3 — tenant activation

Baseline observation: DNS is named as a required service but its protocol set, delegation and fallback are not specified. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§9, 10\]

Documentation treatment: Add resolver TCP and UDP treatment, DNS ownership, TTL/cutover and negative resolver checks.

Still required: Choose resolver endpoints, zones, update authority and any encrypted-DNS profile. Closure evidence: UDP, TCP and truncation/fallback checks plus forbidden-resolver denial.

Trace: [Treatment: SVC §2](../../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md#SVC_s_002)  •  [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)

<a id="gap_G09"></a>

## G09 — Management-domain access

P0 \| Engineering elaboration \| Owner role: Management and identity owners \| G1 — foundation acceptance

Baseline observation: MZ/OOB separation is explained, but no target-by-target management authority schedule is supplied. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§6, 13\]

Documentation treatment: Define operator, executor, support, emergency and guest-administration paths with independent revocation and recovery.

Still required: Assign administrative scopes and surviving OOB dependencies. Closure evidence: Actual role/route review and approved production-path-loss exercise.

Trace: [Treatment: NET §6](../../engineering/fabric/6-management-paths-and-interface-handover.md#NET_s_006)  •  [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)

<a id="gap_G10"></a>

## G10 — Sharing and co-residency decisions

P0 \| Engineering elaboration \| Owner role: Security authority and platform architect \| G0 — design adoption

Baseline observation: The zone-specific baseline is retained; pool, controller, storage and management sharing must be decided together. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§7, 11, 12\]

Documentation treatment: Supply a component-level sharing decision record and placement/evacuation constraints for all vendor realizations.

Still required: Accept zone-authority sharing and HCI controller/storage implications; assess alternatives. Closure evidence: Signed sharing matrix plus placement, migration and restart observations.

Trace: [Treatment: VND §2](../../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md#VND_s_002)  •  [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)

<a id="gap_G11"></a>

## G11 — Common complete reference environment

P1 \| Engineering elaboration \| Owner role: Architecture/platform engineering \| G2 — platform/service acceptance

Baseline observation: The cross-stack example describes one tenant in prose; native resource and handoff accounting is not fully worked. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§15, 23\]

Documentation treatment: Define two tenants, four domains, independent attachments and identical expected outcomes across three stacks.

Still required: Instantiate symbolic resources and select test endpoints in the authorized lab. Closure evidence: Resource/route/service inventory tied to the common fixture.

Trace: [Treatment: VND §1](../../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)

<a id="gap_G12"></a>

## G12 — Nutanix realization detail

P0 \| Vendor validation \| Owner role: Nutanix platform owner \| G2 — platform/service acceptance

Baseline observation: VPC/no-NAT and Flow design is proposed; actual external attachment, placement and lifecycle limits remain unqualified. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§16\]

Documentation treatment: Expand installation versus allocation sequence, forwarding, storage path and operation evidence without assuming resource support.

Still required: Verify installed AOS/Prism/Flow/API/provider/hardware and licence tuple. Closure evidence: Supported-operation matrix, actual handoffs, policy and failure results.

Trace: [Treatment: VND §3](../../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md#VND_s_003)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)

<a id="gap_G13"></a>

## G13 — VMware/NSX upstream realization

P0 \| Vendor validation \| Owner role: VMware/NSX platform owner \| G2 — platform/service acceptance

Baseline observation: Tier-0 VRF or equivalent is proposed; full source retrieval was restricted and no exact supported tuple is selected. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§17\]

Documentation treatment: Retain explicit source limitation; define isolated routing invariants, acceptance alternatives and required vendor confirmation.

Still required: Confirm gateway/VRF/Edge features, limits, entitlements and provider operation coverage. Closure evidence: Current vendor-backed low-level design plus route-propagation and Edge-failure tests.

Trace: [Treatment: VND §4](../../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md#VND_s_004)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)

<a id="gap_G14"></a>

## G14 — OpenStack mandatory policy

P0 \| Vendor validation \| Owner role: OpenStack platform owner \| G2 — platform/service acceptance

Baseline observation: ML2/OVN reference and editable security groups are discussed, but provider-owned policy realization needs a specific design. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§18\]

Documentation treatment: Separate Neutron authority, mandatory control, tenant permits and backend ownership; enumerate alternate attachment paths.

Still required: Select distribution/backend/API policy and persistent mandatory enforcement mechanism. Closure evidence: Default-policy, port authority, relocation, gateway and volume-isolation results.

Trace: [Treatment: VND §5](../../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md#VND_s_005)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)

<a id="gap_G15"></a>

## G15 — Cross-stack communication versus migration

P1 \| Engineering elaboration \| Owner role: Architecture and migration owners \| G0 — design adoption

Baseline observation: Portable, composite and migrated are distinguished; acceptance criteria for choosing among them are not tabulated. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§15, 27\]

Documentation treatment: Add deployment-mode decisions, cross-stack service boundaries and unsupported live-migration handling.

Still required: Choose the required capability and data movement/consistency method. Closure evidence: Approved mode, dependency budget and target recovery evidence.

Trace: [Treatment: VND §6](../../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md#VND_s_006)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<a id="gap_G16"></a>

## G16 — Work-package handoffs

P1 \| Engineering elaboration \| Owner role: Provisioning/service owners \| G2 — platform/service acceptance

Baseline observation: P0–P6 are defined, but there is no minimum handoff record for each owner. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§20, 22, 24\]

Documentation treatment: Define accepted inputs, actual owned outputs, release conditions, downstream consumers and resource-safe reversal.

Still required: Bind packages to selected tools, identities and operating owners. Closure evidence: Each dependency has an accepted handoff; no borrowed broad credentials.

Trace: [Treatment: PROV §1](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)  •  [RA §20](../../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<a id="gap_G17"></a>

## G17 — Independent Day-0 bootstrap

P0 \| Engineering elaboration \| Owner role: Foundation/management owner \| G1 — foundation acceptance

Baseline observation: Bootstrap order is specified, but an explicit minimum surviving service set and transition record is absent. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§21, 13, 14\]

Documentation treatment: Provide bootstrap dependency cuts, temporary authority, steady-state transfer and recovery custody.

Still required: Choose independent console, trust, name/time, artifact and state recovery locations. Closure evidence: Recovery from primary platform unavailability and revoked temporary access.

Trace: [Treatment: PROV §2](../../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md#PROV_s_002)  •  [RA §21](../../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md#RA_s_021)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<a id="gap_G18"></a>

## G18 — Operation-level tool coverage

P0 \| Implementation coverage \| Owner role: Platform and automation engineering \| G2 — platform/service acceptance

Baseline observation: Provider coverage must be checked per operation; the reusable inventory to make that decision is not supplied. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§22, 24\]

Documentation treatment: Add resource-operation matrix with observe/create/update/adopt/replace/delete/recover status and supported alternatives.

Still required: Populate exact resources and support evidence; implement missing owned integrations. Closure evidence: Witnessed lifecycle and failure reconciliation, not a provider-name checkbox.

Trace: [Treatment: PROV §3](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<a id="gap_G19"></a>

## G19 — Activation and rollback safety

P0 \| Engineering elaboration \| Owner role: Provisioning and security-edge owners \| G3 — tenant activation

Baseline observation: Internal verification and post-activation checks exist; detailed irreversible boundaries and safe responses need elaboration. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§23, 24\]

Documentation treatment: Define deny-first assembly, canary/controlled activation, session withdrawal and preservation of newly written data.

Still required: Implement actual activation gates and data-safe recovery actions. Closure evidence: Interrupted-stage and failed-live-check exercises preserve unrelated services.

Trace: [Treatment: PROV §4](../../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md#PROV_s_004)  •  [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<a id="gap_G20"></a>

## G20 — Single-writer and stale executor

P1 \| Implementation coverage \| Owner role: Automation/platform owners \| G3 — tenant activation

Baseline observation: Single ownership and stale plan checks are required; delayed native operations after executor failure are not developed. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§24, 25\]

Documentation treatment: Add ownership transfer, stop-and-discover procedure, outstanding task checks and conditional resumption.

Still required: Qualify locking, credential revocation and task discovery for every executor. Closure evidence: No concurrent competing writers or duplicate allocation after timeout.

Trace: [Treatment: PROV §5](../../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md#PROV_s_005)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)  •  [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)

<a id="gap_G21"></a>

## G21 — Brownfield adoption sequence

P1 \| Engineering elaboration \| Owner role: Existing service and platform owners \| G3 — tenant activation

Baseline observation: Discovery and reviewed adoption are stated, but a complete no-replacement acceptance sequence is not shown. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§25\]

Documentation treatment: Provide discovery, ownership freeze, supported import, no-op plan and canary change gates.

Still required: Inventory live resources and settle existing management ownership. Closure evidence: Reviewed non-destructive plan, rollback boundary and service checks.

Trace: [Treatment: PROV §6](../../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md#PROV_s_006)  •  [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)

<a id="gap_G22"></a>

## G22 — Shared-service dependency placement

P1 \| Engineering elaboration \| Owner role: Shared-service architects \| G2 — platform/service acceptance

Baseline observation: Consumption/administration are distinct; provider service placement and dependency failure are not mapped service by service. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§9, 13, 22\]

Documentation treatment: Add endpoint/management/backend/dependency schedules and distinguish shared endpoints from independent service instances.

Still required: Choose placements, tenancy controls and actual service dependencies. Closure evidence: Service consumption and administrative-denial tests in failure conditions.

Trace: [Treatment: SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)

<a id="gap_G23"></a>

## G23 — Key and certificate recovery

P0 \| Engineering elaboration \| Owner role: Identity, PKI and key owners \| G2 — platform/service acceptance

Baseline observation: Independent custody and no plaintext fallback are required; recovery key lifetime, trust renewal and scope are not worked. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§13, 14\]

Documentation treatment: Add separate key-use/admin/recovery/disposal paths and retained-copy dependency ledger.

Still required: Select approved protocols/module evidence, custody and recovery process. Closure evidence: Rotation, revocation and outage/restore results with retained-data recovery.

Trace: [Treatment: SVC §3](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<a id="gap_G24"></a>

## G24 — Storage copy and attachment lineage

P1 \| Engineering elaboration \| Owner role: Storage and data owners \| G3 — tenant activation

Baseline observation: Storage paths and retained copies are described but no filled copy lineage or attachment lifecycle is supplied. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§12, 27\]

Documentation treatment: Add authoritative copy/attachment records, data access paths, inherited category and disposal checkpoints.

Still required: Map real backend, image, snapshot, clone, replica and backup mechanisms. Closure evidence: Foreign attachment/export denials and retained-copy disposal accounting.

Trace: [Treatment: SVC §4](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<a id="gap_G25"></a>

## G25 — Backup and isolated restore

P0 \| Engineering elaboration \| Owner role: Backup and recovery owners \| G2 — platform/service acceptance

Baseline observation: Restore is the acceptance metric; proxy/API/data paths and reconstruction dependencies need more detail. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§12, 14, 27\]

Documentation treatment: Provide capture/transfer/repository separation and stepwise isolated restore with key/catalogue prerequisites.

Still required: Choose supported capture/consistency methods and approve RTO/RPO and retention. Closure evidence: Recover useful test data and demonstrate isolation before reconnecting.

Trace: [Treatment: SVC §5](../../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md#SVC_s_005)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<a id="gap_G26"></a>

## G26 — Site-loss and failback ownership

P0 \| Engineering elaboration \| Owner role: Continuity and data owners \| G4 — recovery/operational acceptance

Baseline observation: Fencing and failback are required; partition, alternate writer and reverse synchronization decisions are not tabulated. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§14, 27\]

Documentation treatment: Define failure/authority matrix, writer exclusion, activation and return-to-primary sequence.

Still required: Populate surviving dependencies and specific fencing/consistency method. Closure evidence: Observed site/partition recovery with measured objectives and safe failback.

Trace: [Treatment: SVC §6](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<a id="gap_G27"></a>

## G27 — Measured capacity and admission

P1 \| Engineering elaboration \| Owner role: Capacity and platform owners \| G2 — platform/service acceptance

Baseline observation: Capacity principle is present; no worked multi-resource admission or edge-context accounting example exists. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§4, 14, 26\]

Documentation treatment: Add unit-aware resource ledger and illustrative surviving-capacity calculations; distinguish reservations from observed use.

Still required: Measure capacity under agreed failure/maintenance and security feature load. Closure evidence: Approved service envelope with binding bottleneck and growth trigger.

Trace: [Treatment: QUAL §3](../site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)

<a id="gap_G28"></a>

## G28 — Service objectives and retention parameters

P0 \| Site/service decision \| Owner role: Service/data owners \| G2 — platform/service acceptance

Baseline observation: Actual SLO/RTO/RPO and retention remain implementation responsibilities. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§12, 14, 26\]

Documentation treatment: Provide a parameter decision sheet with measurement scope, approving role, feasibility proof and dependencies.

Still required: Supply business requirements, retention obligations and measured feasibility. Closure evidence: Approved values and test method; no unspecified production promise.

Trace: [Treatment: QUAL §4](../site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)

<a id="gap_G29"></a>

## G29 — Qualification applicability and sequencing

P0 \| Qualification evidence \| Owner role: Assurance engineering \| G2 — platform/service acceptance

Baseline observation: 80 inherited tests and 12 addenda remain not-run; not every test applies at every gate. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§28, 30\]

Documentation treatment: Separate first-stack qualification from second-stack portability and use assertion-level applicability with explicit not-applicable authority.

Still required: Select applicable procedures and execute on the actual tuple. Closure evidence: All mandatory observations supported; blocked/not-run never count as pass.

Trace: [Treatment: QUAL §5](../site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<a id="gap_G30"></a>

## G30 — Control inheritance and external dependencies

P0 \| Engineering elaboration \| Owner role: Security authority and service owners \| G0 — design adoption

Baseline observation: Applicable controls and responsibility are required; organizational/physical control inheritance is not assembled. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§1, 26, 28\]

Documentation treatment: Add provider/tenant/shared/inherited dispositions including physical, personnel, maintenance and training interfaces.

Still required: Select actual catalogue controls/parameters and accept inherited evidence. Closure evidence: Control allocation, residual gaps and formal decision references.

Trace: [Treatment: QUAL §6](../site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md#QUAL_s_006)  •  [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)

<a id="gap_G31"></a>

## G31 — Operating ownership and incident behaviour

P1 \| Engineering elaboration \| Owner role: Operations/service management \| G4 — recovery/operational acceptance

Baseline observation: Roles are described in prose; a decision-level accountability and handover schedule is absent. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§25, 26, 27\]

Documentation treatment: Add accountable decision owner matrix, containment precedence, monitoring questions and handover acceptance.

Still required: Name teams/on-call owners and integrate local incident/change processes. Closure evidence: Accepted handover, credential review and scoped incident exercise.

Trace: [Treatment: QUAL §7](../site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)  •  [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)

<a id="gap_G32"></a>

## G32 — Version and source provenance

P1 \| Vendor validation \| Owner role: Platform engineering and architecture \| G2 — platform/service acceptance

Baseline observation: Some references are historic, inherited or access-limited; no source review state should be mistaken for qualification. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§15, 16, 17, 18, 24\]

Documentation treatment: Record review status separately from source edition; require exact installed tuple and supported-operation evidence.

Still required: Obtain unavailable current vendor material and select installed versions. Closure evidence: Dated compatibility record and qualified lifecycle results.

Trace: [Treatment: VND §7](../../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md#VND_s_007)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<a id="gap_G33"></a>

## G33 — Bounded extensions

P2 \| Scope boundary \| Owner role: Extension service owner \| G0 — extension adoption

Baseline observation: Bare metal and containers are explicitly extensions, not complete implementations. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§19\]

Documentation treatment: Keep them outside the base offered service until dedicated topology, ownership and recovery qualification exists.

Still required: Develop extension-specific low-level design only when requested as a service. Closure evidence: Approved scope and complete applicable extension qualification.

Trace: [Treatment: QUAL §8](../site-qualification/8-extensions-and-release-maintenance.md#QUAL_s_008)  •  [RA §19](../../architecture/reference/19-physical-workloads-and-future-platform-extensions.md#RA_s_019)

<a id="gap_G34"></a>

## G34 — Knowledge maintenance and cross-link integrity

P2 \| Knowledge organization \| Owner role: Architecture document owner \| G0 — design adoption

Baseline observation: A growing document set can duplicate policy or allow supplement drift. \[[B2](06-references-parent-basis-and-external-context.md#GM_src_B2) §§1, 30\]

Documentation treatment: Assign a primary home per topic, stable parent anchors and a release-wide link/requirement mapping check.

Still required: Assign maintaining owners and release cadence. Closure evidence: Consistent version set, validated links and approved change record.

Trace: [Treatment: GM §2](2-primary-knowledge-homes-and-cross-cutting-changes.md#GM_s_002)  •  [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

[Previous chapter](2-primary-knowledge-homes-and-cross-cutting-changes.md) · [Chapter index](README.md) · [Next chapter](4-open-decision-package-for-implementation.md)
