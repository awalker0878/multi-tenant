# 7. Tenant provisioning and controlled production activation

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx) · [Chapter index](README.md)

> **Source:** IK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b16b8843bfbafd1b417d611903f5b8038f4794efd4f22c995bee1cb36f9ebb41 -->
<a id="IK_07"></a>

Normal tenant allocation consumes accepted capacity. Production activation has additional prerequisites that a successful infrastructure build cannot waive.

Baseline and related records: [RA §23](../../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md#RA_s_023)  •  [WD §9](../../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md#WD14_S09)  •  [IT §7](../../templates/implementation-mop/7-gate-decision-and-production-activation.md#IT_07)


<a id="source-table-68"></a>

| Sequence | Execute within accepted scope | Stop / preserve |
| --- | --- | --- |
| 1 — Confirm prerequisites | Check G0/G1/G2 for the offered service; confirm current service authority, initial G4 readiness and owner acceptance requirements. | Missing scope or evidence prevents production activation. |
| 2 — Reserve and establish scope | Resolve eligible cell/pools; reserve compute, storage, addresses and edge slots; establish tenant/domain ownership. | No guessed addresses or capacity borrowed from failure reserve. |
| 3 — Denied networks and boundary | Create native networks/gateways and mandatory policies before endpoint connection; configure paired edge routes and flows under their owner. | No fallback public/default route; unverified resources remain isolated. |
| 4 — Resources and services | Use approved images, owned disks and eligible hosts; register names, identities, telemetry and protection. | Do not relax placement or grant broad service-management access to finish a build. |
| 5 — Verify and review | Compare actual placement, attachments, permitted/denied paths, service scope, protection and current evidence. | Unknown, stale or failed mandatory observation keeps the environment restricted. |
| 6 — Controlled activation | Authorized service owner accepts the exact scope; enable only approved exposure and verify the live path. | On failed activation, withdraw exposure while preserving owned data and evidence. |
| 7 — Confirm as-built | Record native identities, actual state, acceptance and support handover. | This confirms already assigned owners; it is not where readiness is first discovered. |

G4 initial readiness precedes G3 production activation. Continuing G4 exercises after activation do not replace the initial proof supporting a promised service. Restricted fixture permission is a separate record.

The [production activation assurance gate](../../engineering/production-activation-and-initial-readiness-assurance.md) turns these dependencies into a fail-closed evidence record. A ready result still does not authorize exposure; only the accountable external authority can execute the activation change.

[Previous chapter](6-restricted-qualification-and-meaningful-observations.md) · [Chapter index](README.md) · [Next chapter](8-interrupted-work-brownfield-adoption-and-change.md)
