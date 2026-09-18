# 5. Management, data and service dependencies

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/HLD_and_Architecture_Review_Template.docx) · [Chapter index](README.md)

> **Source:** AT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 911b87e6a36d903a12535d16d75f1875c0cefb6b72c462895f7c2559b556708c -->
<!-- SOURCE-BLOCK AT:51 BEGIN -->

<a id="AT_05"></a>

<!-- SOURCE-BLOCK AT:51 END -->

<!-- SOURCE-BLOCK AT:52 BEGIN -->

Working record for AK-03/05. Complete the responses and attach the referenced evidence or drawing; do not replace an unresolved item with an unsupported assumption.

<!-- SOURCE-BLOCK AT:52 END -->

<!-- SOURCE-BLOCK AT:53 BEGIN -->

Baseline and related records: [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)

<!-- SOURCE-BLOCK AT:53 END -->

<!-- SOURCE-BLOCK AT:54 BEGIN -->


<a id="source-table-54"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| V05 administration | Privileged origin, management boundaries, actual authority and emergency path. | {{AT\_V05}} |
| V06 compute/data | Host pools, virtual-disk and guest-data paths, copies, storage control and key scope. | {{AT\_V06}} |
| V07 services | Consumption interface, initiating client, reply path and backend entitlement. | {{AT\_V07}} |
| Bootstrap dependencies | Services needed before platform APIs exist and transfer to steady state. | {{AT\_BOOTSTRAP}} |
| Trust/copy custody | Separate use, administration, recovery and disposal responsibilities. | {{AT\_TRUST}} |
| Dependency register | Controlled record locating inherited services and shared failure impacts. | {{AT\_DEPENDENCIES}} |

<!-- SOURCE-BLOCK AT:54 END -->

<!-- SOURCE-BLOCK AT:55 BEGIN -->

<!-- SOURCE-BLOCK AT:55 END -->

<!-- SOURCE-BLOCK AT:56 BEGIN -->

Reviewer: guest storage encryption does not invent a guest KMS route; backup orchestration and data movement are separate paths.

<!-- SOURCE-BLOCK AT:56 END -->

<!-- SOURCE-BLOCK AT:57 BEGIN -->

Record status: Draft / In review / Accepted for stated scope / Returned for revision. Use the actual review record, not this prompt, as authority.

<!-- SOURCE-BLOCK AT:57 END -->

<!-- SOURCE-BLOCK AT:58 BEGIN -->

<!-- SOURCE-BLOCK AT:58 END -->

[Previous chapter](4-logical-tenancy-security-and-traffic-views.md) · [Chapter index](README.md) · [Next chapter](6-architecture-decision-record.md)
