# 2. Physical placement and the sharing decision

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<!-- SOURCE-BLOCK VND:35 BEGIN -->

<a id="__RefHeading___Toc4810_865363315"></a>
<a id="VND_s_002"></a>

<!-- SOURCE-BLOCK VND:35 END -->

<!-- SOURCE-BLOCK VND:36 BEGIN -->

Parent architecture: [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<!-- SOURCE-BLOCK VND:36 END -->

<!-- SOURCE-BLOCK VND:37 BEGIN -->

A security-domain boundary is logical, but compromise and failure can cross shared physical or administrative dependencies. Document sharing separately for compute hosts, cluster control, storage controllers/media, transport, security-edge hardware, management, backup and keys. The parent retains zone-specific host pools as its baseline. Any alternative requires the appropriate security decision; an isolation label or platform project is not sufficient evidence. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §§7, 11–14; [S03](08-references-parent-basis-and-external-context.md#VND_src_S03)\]

<!-- SOURCE-BLOCK VND:37 END -->

<!-- SOURCE-BLOCK VND:38 BEGIN -->


<a id="source-table-38"></a>

| Layer | Baseline reference placement | What must be decided and demonstrated |
| --- | --- | --- |
| Management/control | Protected management capacity and scoped administrative domains. | Exact hosting/recovery dependency; management availability during workload-cell failure. |
| OZ and RZ compute | Eligible zone-specific pools; compatible tenant sharing only when approved. | Actual domain authorities permitted to share, scheduler restrictions and restart/evacuation behaviour. |
| Security-edge services | Separately governed capacity with bounded failure and privilege effects. | Dedicated or shared hardware, per-context routing/policy and surviving inspection load. |
| Storage/controller | Backend and copy ownership explicitly recorded. | HCI controller/media sharing, access scope, encryption, rebuild and copy operations. |
| Transport | Shared fabric may carry isolated platform and service paths. | No route/connected-path bypass; actual rack/uplink common failures. |
| Recovery infrastructure | Preauthorized target with usable keys, names, catalogues and eligible capacity. | No dependency on the sole failed primary resource to recover itself. |

<!-- SOURCE-BLOCK VND:38 END -->

<!-- SOURCE-BLOCK VND:39 BEGIN -->

<!-- SOURCE-BLOCK VND:39 END -->

<!-- SOURCE-BLOCK VND:40 BEGIN -->

Choose a sharing outcome at each layer: dedicated physical, dedicated logical on shared hardware, or explicitly approved shared service. Record who can administer the layer and what a compromise at that layer can affect. Physical dedication of hosts does not make shared identity, storage, security edge or backup independent. Failure-domain independence and administrative independence are two different observations.

<!-- SOURCE-BLOCK VND:40 END -->

<!-- SOURCE-BLOCK VND:41 BEGIN -->

The low-level design translates the decision into scheduler restrictions, host/cluster membership, service placement, credentials and fail actions. Test normal placement, resize, live mobility where offered, evacuation, HA restart and restore. A lack of eligible spare capacity should produce a defined service degradation or rejection, not an unapproved move across a zone or dedication boundary.

<!-- SOURCE-BLOCK VND:41 END -->

<!-- SOURCE-BLOCK VND:42 BEGIN -->

Related engineering: [Physical dependency worksheet](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)  •  [Control inheritance](../../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md#QUAL_s_006)

<!-- SOURCE-BLOCK VND:42 END -->

[Previous chapter](1-one-reference-environment-three-native-realizations.md) · [Chapter index](README.md) · [Next chapter](3-nutanix-component-path-and-lifecycle-realization.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0008 — Preserve zone-aware host placement and disclose every shared layer](../../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

<!-- END GENERATED DECISION LINKS -->
