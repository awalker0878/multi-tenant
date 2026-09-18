# 8. Workload Security Domain

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
The WSD is the primary lifecycle object. It captures a workload’s required security and service intent without prescribing the implementation. A WSD can attach to one or more Security Domain Instances depending on its application topology.


<a id="source-table-101"></a>

| WSD Attribute | Purpose |
| --- | --- |
| Security Profile | Control baseline and information-security context. |
| Assurance Profile | Required strength of physical/logical isolation. |
| Placement Profile | Authorized platforms, sites, availability, sovereignty and lifecycle constraints. |
| Networks | Workload internetworks and their zone association. |
| Flow Intentions | Explicit application communication requirements. |
| Service Bindings | DNS, NTP, identity, PKI, logging, backup and similar services. |
| Exposure | Internet/public, enterprise, extranet, partner, migration or other external connections. |
| Evidence Profile | Tests and evidence required before Service Ready. |


<a id="source-table-102"></a>

| WSD-001 | Every managed workload SHALL belong to a WSD or an explicitly documented equivalent lifecycle object. |
| --- | --- |


<a id="source-table-103"></a>

| WSD-002 | The WSD SHALL contain security and connectivity intent; it SHALL NOT contain vendor-specific infrastructure identifiers in the consumer contract. |
| --- | --- |

[Previous chapter](7-tenant-namespace.md) · [Chapter index](README.md) · [Next chapter](9-security-domain-instance.md)
