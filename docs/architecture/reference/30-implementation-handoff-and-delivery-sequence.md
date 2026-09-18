# 30. Implementation handoff and delivery sequence

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:408 BEGIN -->

<a id="__RefHeading___Toc3698_865363315"></a>
<a id="RA_s_030"></a>

<!-- SOURCE-BLOCK RA:408 END -->

<!-- SOURCE-BLOCK RA:409 BEGIN -->

The architecture handoff converts the selected reference into a buildable design for a named site and platform tuple. It is not another application-design exercise. The implementation team supplies the following records, with accountable owners and approval gates. Unresolved values are blocking decisions at their indicated gate, not placeholders that can be silently replaced with product defaults.

<!-- SOURCE-BLOCK RA:409 END -->

<!-- SOURCE-BLOCK RA:410 BEGIN -->


<a id="source-table-410"></a>

| Required design record | Contents | Must be resolved before |
| --- | --- | --- |
| Site and cell deployment | Physical inventory; racks/power/failure groups; cell boundaries; shared/dedicated resources | Physical commissioning |
| Network design | Port/link roles; underlay addressing/ASNs; routing/multihoming; VLAN/VNI/RT authority where used; MTU and attachments | Fabric and platform transport acceptance |
| Management and trust | MZ/OOB topology; admin access; identity/key/certificate dependencies; bootstrap/recovery path | Privileged production operation |
| Vendor realization | Exact stack/API/provider releases; supported hardware; licences; gateway/storage/host topology and restrictions | Platform qualification |
| Zone and path schedule | Domain authorities; two-zone relationships; prefixes; flow direction; enforcement and return paths | Tenant connectivity activation |
| Capacity and service parameters | Usable/surviving capacity; quotas/reserves; performance; SLO/RTO/RPO; limits and recovery cadence | Advertising the service class |
| Provisioning implementation | Work packages; ownership; tool/provider operation coverage; state/credentials; dependency gates and error handling | Automated tenant allocation |
| Operating and assurance pack | As-built inventory; support/patch/monitoring; test evidence; exceptions; runbooks; handover and authorization | Service Ready |

<!-- SOURCE-BLOCK RA:410 END -->

<!-- SOURCE-BLOCK RA:411 BEGIN -->

<!-- SOURCE-BLOCK RA:411 END -->

<!-- SOURCE-BLOCK RA:412 BEGIN -->

## Delivery sequence

<!-- SOURCE-BLOCK RA:412 END -->

<!-- SOURCE-BLOCK RA:413 BEGIN -->

First adopt the topology, isolation choices and ownership model. Commission one site foundation and a small first-platform cell, then the management/security/shared-service dependencies needed for a complete tenant environment. Implement the minimum end-to-end provisioning path across those owners. Prove two-tenant isolation, the approved zone path, changes, recovery and retirement before expanding feature count or scale.

<!-- SOURCE-BLOCK RA:413 END -->

<!-- SOURCE-BLOCK RA:414 BEGIN -->

Next realize the same architecture on a second stack and rehearse a representative migration or restore. Use the result to correct resource abstractions and service promises. Add the remaining platform and optional service classes through their own qualification. Do not attempt to achieve portability by making every vendor reproduce a proprietary topology chosen for the first one.

<!-- SOURCE-BLOCK RA:414 END -->

<!-- SOURCE-BLOCK RA:415 BEGIN -->

The architecture may be adopted before every target stack is ready, provided unsupported classes remain excluded. Production use still requires named operating owners, actual service parameters, applicable controls and current qualification/authorization evidence. The controlled delivery backlog distinguishes missing design decisions, missing automation coverage and tests not yet executed; those are different kinds of work.

<!-- SOURCE-BLOCK RA:415 END -->

<!-- SOURCE-BLOCK RA:416 BEGIN -->

Definition of done for this revision — The revised document provides the infrastructure topology, logical boundaries, vendor-specific reference realizations, shared-service interfaces, provisioning sequence, Terraform boundaries and lifecycle acceptance model. The accompanying mapping preserves the v1.1 requirement and assurance baseline and records the architectural corrections. It is not a claim that the environment has been deployed or qualified.

<!-- SOURCE-BLOCK RA:416 END -->

<!-- SOURCE-BLOCK RA:417 BEGIN -->

Use GM §3 as the live design-gap map and GM §4 as the implementation decision package. Each record links this parent to the primary engineering treatment and distinguishes supplied documentation from open site/vendor/build/evidence work. G0–G4 are coordination gates for design adoption, foundation acceptance, platform/service acceptance, tenant activation and operational/recovery acceptance; they map to existing organizational processes rather than creating a required new application.

<!-- SOURCE-BLOCK RA:417 END -->

<!-- SOURCE-BLOCK RA:418 BEGIN -->

Related engineering: [GM §3 — Detailed gap register and treatment](../../assurance/gap-map/3-detailed-gap-register-and-treatment.md#GM_s_003)  •  [QUAL §1 — From proposed architecture to accepted service](../../assurance/site-qualification/1-from-proposed-architecture-to-accepted-service.md#QUAL_s_001)  •  [QUAL §2 — Site low-level design and dependency schedule](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)

<!-- SOURCE-BLOCK RA:418 END -->

[Previous chapter](29-architecture-decisions-and-alternatives.md) · [Chapter index](README.md) · [Next chapter](31-appendix-a-revision-scope-and-baseline-traceability.md)
