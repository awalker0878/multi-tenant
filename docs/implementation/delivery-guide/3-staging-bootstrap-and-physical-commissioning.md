# 3. Staging, bootstrap and physical commissioning

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx) · [Chapter index](README.md)

> **Source:** IK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b16b8843bfbafd1b417d611903f5b8038f4794efd4f22c995bee1cb36f9ebb41 -->
<!-- SOURCE-BLOCK IK:32 BEGIN -->

<a id="IK_03"></a>

<!-- SOURCE-BLOCK IK:32 END -->

<!-- SOURCE-BLOCK IK:33 BEGIN -->

Use RB-00 and RB-01. Staging is part of implementation readiness, not evidence that equipment has been commissioned.

<!-- SOURCE-BLOCK IK:33 END -->

<!-- SOURCE-BLOCK IK:34 BEGIN -->

Baseline and related records: [RA §21](../../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md#RA_s_021)  •  [ET §2](../../templates/lld/2-physical-inventory-facility-and-port-schedule.md#ET_02)  •  [PROV §2](../provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md#PROV_s_002)

<!-- SOURCE-BLOCK IK:34 END -->

<!-- SOURCE-BLOCK IK:35 BEGIN -->


<a id="source-table-35"></a>

| Checkpoint | Required action and observation | Stop condition |
| --- | --- | --- |
| Release and scope | Match change authorization, exact inventory, LLD revision, signed/checksummed artifacts and permitted window. | Unapproved change, inconsistent inventory or unknown resource owner. |
| Site safety and physical work | Have qualified personnel perform installation using approved facility and manufacturer procedures. Record completion, access, rack/power/failure-group and cable results. | Missing facility release, unsafe conditions or installation outside the accepted design. |
| Supply and baseline | Verify received equipment, licenses, support, firmware/driver compatibility and trusted software source. Retain media/part custody where required. | Unknown support combination, altered artifact or unaccounted component. |
| Restricted management | Establish the approved console/OOB and initial privileged trust; restrict target access and register temporary grants. | Default credentials or a tenant path exposes privileged management. |
| Minimum dependencies | Verify trusted time/name/identity or approved emergency alternatives, certificate trust and artifact access. | Required dependency has no accepted endpoint or independent recovery method. |
| Foundation observation | Use the approved configuration mechanism; observe links, control policy, MTU, allowed adjacency and surviving access. | Unexpected route/port, missing policy or failed recovery access. |
| Handover | Store actual configuration, ownership, recovery copy, telemetry and open deviations; obtain G1 scope acceptance. | Required observations absent or unresolved critical deviations. |

<!-- SOURCE-BLOCK IK:35 END -->

<!-- SOURCE-BLOCK IK:36 BEGIN -->

<!-- SOURCE-BLOCK IK:36 END -->

<!-- SOURCE-BLOCK IK:37 BEGIN -->

Do not store production secrets in this kit. Record a protected custody reference and the authorized role. A temporary bootstrap credential is not a permanent exception to separation of duties.

<!-- SOURCE-BLOCK IK:37 END -->

<!-- SOURCE-BLOCK IK:38 BEGIN -->

<!-- SOURCE-BLOCK IK:38 END -->

[Previous chapter](2-work-packages-dependencies-and-authority.md) · [Chapter index](README.md) · [Next chapter](4-native-platform-commissioning-tracks.md)
