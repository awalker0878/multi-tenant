# 7. Tenant Namespace

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
A Tenant Namespace establishes administrative isolation. It is the root for RBAC assignments, quotas, ownership metadata, chargeback/showback, policy ownership, and service inventory. It is not automatically a single network or security zone.


<a id="source-table-96"></a>

| Tenant Namespace SHALL define | Notes |
| --- | --- |
| Unique tenant identifier | Stable, non-semantic identifiers are preferred for automation. |
| Identity groups and roles | Mapped from enterprise identity; local break-glass accounts are exceptional. |
| Quota and entitlement | Compute, storage, network, public exposure, backup, and service limits. |
| Default security profile | May be overridden only by approved WSD policy. |
| Ownership metadata | Service owner, technical owner, security authority, cost centre/service code as applicable. |
| Lifecycle state | Requested, Active, Restricted, Suspended, Retiring, Retired. |


<a id="source-table-97"></a>

| TEN-001 | Cross-tenant routing SHALL be denied by default even when two tenants use the same zone class. |
| --- | --- |


<a id="source-table-98"></a>

| TEN-002 | Tenant administrators SHALL NOT have authority to modify provider management, security-edge infrastructure, physical fabric, or another tenant namespace. |
| --- | --- |

[Previous chapter](6-high-level-reference-architecture.md) · [Chapter index](README.md) · [Next chapter](8-workload-security-domain.md)
