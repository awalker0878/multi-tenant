# 20. Workload Microsegmentation

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
A security zone may contain multiple internetworks. Microsegmentation is therefore the primary mechanism for separating applications and tiers that are allowed to reside in the same Security Domain Instance. Identity/metadata-based controls are preferred where platform capabilities support them because policy follows workload identity instead of depending only on addresses.


<a id="source-table-182"></a>

| MICRO-001 | WSD-to-WSD and tier-to-tier communication inside a shared Security Domain SHOULD default to deny unless an approved policy permits it. |
| --- | --- |


<a id="source-table-183"></a>

| MICRO-002 | Platform metadata used for security policy SHALL be managed, validated, and protected from unauthorized tenant modification. |
| --- | --- |

[Previous chapter](19-public-ingress-and-internet-egress.md) · [Chapter index](README.md) · [Next chapter](21-multi-site-and-disaster-recovery-network-design.md)
