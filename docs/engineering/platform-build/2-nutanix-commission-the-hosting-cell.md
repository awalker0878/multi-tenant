# 2. Nutanix: commission the hosting cell

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<!-- SOURCE-BLOCK PBS:28 BEGIN -->

<a id="PBS_02"></a>

<!-- SOURCE-BLOCK PBS:28 END -->

<!-- SOURCE-BLOCK PBS:29 BEGIN -->

P2 establishes AHV/AOS and protected Prism/Flow management for a defined cell. Cluster installation is distinct from allocating a tenant’s VPC, VM or data.

<!-- SOURCE-BLOCK PBS:29 END -->

<!-- SOURCE-BLOCK PBS:30 BEGIN -->

Design basis and related records: [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [VND §3](../platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md#VND_s_003)  •  [VC §2](../vendor-cards/2-nutanix-realization-card.md#VC_02)

<!-- SOURCE-BLOCK PBS:30 END -->

<!-- SOURCE-BLOCK PBS:31 BEGIN -->

The engineering release supplies hardware and firmware compatibility, cluster membership, management and recovery paths, adopted co-residency, supported storage/protection classes, actual licences, and the selected AOS/Prism/Flow/API/provider combination. Treat controller/storage sharing as part of the security and failure analysis, not merely an internal implementation detail.

<!-- SOURCE-BLOCK PBS:31 END -->

<!-- SOURCE-BLOCK PBS:32 BEGIN -->


<a id="source-table-32"></a>

| Commissioned output | Build specification | Acceptance observation |
| --- | --- | --- |
| Cluster and management | Accepted installation artifacts; named management interfaces, trust and scoped roles. | Native health, expected membership, protected administrative access and recoverable configuration. |
| Eligible host/storage pools | Enforced workload placement, supported images/boot modes, data/key scope and reserve. | Disallowed placement rejected; intended disk access and protection prerequisites available. |
| Network and external capacity | Overlay transport plus isolated or explicitly qualified external handoff slots. | Transport MTU, actual gateway behaviour, route ownership and no common-connected bypass. |
| Mandatory policy foundation | Provider-controlled selectors, baseline rules and authorization limits. | Tenant identity cannot alter mandatory membership or expand baseline permissions. |
| Operational dependencies | Accepted names, time, logging, keys, images and backup/recovery interfaces. | Correct clients, scope and independent recovery of the dependencies needed to restart the cell. |

<!-- SOURCE-BLOCK PBS:32 END -->

<!-- SOURCE-BLOCK PBS:33 BEGIN -->

<!-- SOURCE-BLOCK PBS:33 END -->

<!-- SOURCE-BLOCK PBS:34 BEGIN -->

The official provider repository publishes version-specific compatibility and resource/lifecycle notes. Use these as inputs to the actual support decision, not as proof that a named resource supports every intended update or recovery action. This document does not select a provider release. \[D03\]

<!-- SOURCE-BLOCK PBS:34 END -->

<!-- SOURCE-BLOCK PBS:35 BEGIN -->

Verified mechanism source: [D03 — Nutanix Terraform provider official repository](https://github.com/nutanix/terraform-provider-nutanix)

<!-- SOURCE-BLOCK PBS:35 END -->

<!-- SOURCE-BLOCK PBS:36 BEGIN -->

The cell remains a safeguarded candidate until applicable qualification is complete. Record installation receipts separately from the later test campaign, and stop advertising any service class whose required attachment or policy behaviour remains unresolved.

<!-- SOURCE-BLOCK PBS:36 END -->

<!-- SOURCE-BLOCK PBS:37 BEGIN -->

Continue with: [QCP §1](../../assurance/qualification-campaign/1-select-the-qualification-scope-and-acceptance-claim.md#QCP_01)  •  [PBS §3](3-nutanix-realize-a-tenant-and-its-workload-domains.md#PBS_03)

<!-- SOURCE-BLOCK PBS:37 END -->

<!-- SOURCE-BLOCK PBS:38 BEGIN -->

<!-- SOURCE-BLOCK PBS:38 END -->

[Previous chapter](1-choose-the-platform-boundary-and-configuration-owner.md) · [Chapter index](README.md) · [Next chapter](3-nutanix-realize-a-tenant-and-its-workload-domains.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs](../../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<!-- END GENERATED DECISION LINKS -->
