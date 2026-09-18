# 5. Keep fabric authority separate from tenant routing

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx) · [Chapter index](README.md)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->
<!-- SOURCE-BLOCK NBD:60 BEGIN -->

<a id="NBD_05"></a>

<!-- SOURCE-BLOCK NBD:60 END -->

<!-- SOURCE-BLOCK NBD:61 BEGIN -->

The physical fabric carries transport and explicitly assigned physical routing services; it does not inherit every tenant route merely because it connects the platform hosts.

<!-- SOURCE-BLOCK NBD:61 END -->

<!-- SOURCE-BLOCK NBD:62 BEGIN -->

Design basis and related records: [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [NET §1](../fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [VC §5](../vendor-cards/5-physical-fabric-and-oob-realization-card.md#VC_05)

<!-- SOURCE-BLOCK NBD:62 END -->

<!-- SOURCE-BLOCK NBD:63 BEGIN -->

Publish the underlay’s device/link inventory, address and ASN authority, allowed peers, explicit import/export policy, route limits, control-plane protection and maintenance method. Specify which platform tunnel endpoints and service attachments consume that transport. A tenant request consumes accepted capacity; a new physical attachment class or an exhausted pool returns to foundation engineering.

<!-- SOURCE-BLOCK NBD:63 END -->

<!-- SOURCE-BLOCK NBD:64 BEGIN -->


<a id="source-table-64"></a>

| Engineering question | Required design answer | Observation before acceptance |
| --- | --- | --- |
| What routing belongs here? | List transport and approved physical-domain prefixes; exclude unintended tenant imports. | Compare accepted and actual advertisements, next hops and selected forwarding. |
| Where is EVPN needed? | Select only the fabric services requiring it; assign RD/RT/VNI scope and gateway ownership. | Inspect imports and connected paths rather than trusting common identifier conventions. |
| How are endpoints multihomed? | Choose the supported host/appliance mechanism and its peer/segment dependencies. | Observe link and peer failure, orphan behaviour, restoration and management reachability. |
| How do vendor stacks connect? | Use the approved routed/security handoff; direct overlay federation is not the base service. | Confirm transport reachability without unapproved routing or policy authority crossing stacks. |

<!-- SOURCE-BLOCK NBD:64 END -->

<!-- SOURCE-BLOCK NBD:65 BEGIN -->

<!-- SOURCE-BLOCK NBD:65 END -->

<!-- SOURCE-BLOCK NBD:66 BEGIN -->

Assign one writer to each switch configuration or independently owned subresource. A vendor installer, a network automation system and Terraform must not each believe they own the same routing or interface object. Before adoption, compare intended configuration with the live inventory and review a non-destructive change scope.

<!-- SOURCE-BLOCK NBD:66 END -->

<!-- SOURCE-BLOCK NBD:67 BEGIN -->

Physical installation, power, optics and cabling are accepted through qualified site personnel and manufacturer procedures. This document supplies ownership and acceptance records, not hazardous installation instructions or unverified network-OS commands.

<!-- SOURCE-BLOCK NBD:67 END -->

<!-- SOURCE-BLOCK NBD:68 BEGIN -->

Continue with: [PBS §1](../platform-build/1-choose-the-platform-boundary-and-configuration-owner.md#PBS_01)  •  [OPS §3](../../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md#OPS_03)

<!-- SOURCE-BLOCK NBD:68 END -->

<!-- SOURCE-BLOCK NBD:69 BEGIN -->

<!-- SOURCE-BLOCK NBD:69 END -->

[Previous chapter](4-budget-address-families-and-encapsulation-precisely.md) · [Chapter index](README.md) · [Next chapter](6-issue-an-interface-control-and-handoff-record.md)
