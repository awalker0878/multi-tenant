# 5. Shared security, services and protection

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx) · [Chapter index](README.md)

> **Source:** IK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b16b8843bfbafd1b417d611903f5b8038f4794efd4f22c995bee1cb36f9ebb41 -->
<a id="IK_05"></a>

Use RB-05. Shared services and ZIP capacity are provider infrastructure, not incidental tenant modules.

Baseline and related records: [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [WD §7](../../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md#WD14_S07)


<a id="source-table-53"></a>

| Service boundary | Commissioning observation | Receipt / responsible owner |
| --- | --- | --- |
| EC/SE and domain handoffs | Correct context membership, permitted prefixes, connected routes, forward/reply symmetry, no alternative inspection bypass; management separately controlled. | Context/interface identities, policies, capacity and test traces / security-edge owner. |
| Names, addresses and time | One authoritative allocator per delegated scope; forward/reverse lifecycle and reuse; DNS UDP/TCP and fallback; selected time service. | Allocations, names, TTL/lease constraints, protocol checks / network-service owner. |
| Identity and privileges | Actual native roles match approved duties; tenant cannot modify baseline or foreign resources; recovery path is controlled. | Role and target-scope review, grant/revocation evidence / identity and platform owners. |
| Certificates and keys | Correct client/issuer/trust relationship, endpoint validation, use versus administration, retained-copy key continuity; no plaintext fallback. | Key/certificate references and observed recovery behaviour / trust custodians. |
| Logging and monitoring | Events carry usable domain/workload identity; approved collection and time; loss/buffering visible; no broad management access. | Event examples, coverage and alert routing / operations owner. |
| Storage and protection | Owned attachments/copies, supported capture path, separate transfer/admin, retained catalogue and protected keys; actual isolated restore. | Copy lineage, protection assignment and restore result / storage and backup owners. |

Service reachability is not service entitlement. A shared resolver or repository must not forward tenant traffic or grant administrative rights. For the dedicated service-handoff example, service replies must select the originating tenant context; a convenient default route is not proof of symmetric enforcement.

[Previous chapter](4-native-platform-commissioning-tracks.md) · [Chapter index](README.md) · [Next chapter](6-restricted-qualification-and-meaningful-observations.md)
