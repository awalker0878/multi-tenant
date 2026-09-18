# 32. Policy as Code and Security Admission

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Security admission rejects invalid architectures before provider execution. Policies should evaluate portable intent rather than only vendor plans, with provider-plan policies providing a second line of defense.


<a id="source-table-265"></a>

| Example Request | Admission Result |
| --- | --- |
| Restricted zone directly to public network | DENY |
| Tenant workload directly to MZ/OOB | DENY |
| Arbitrary BGP peer | DENY |
| Disable mandatory logging | DENY |
| Unsupported assurance profile on target platform | DENY |
| Approved internal flow through declared ZIP path | ALLOW |
| Approved DNS service binding | ALLOW |


<a id="source-table-266"></a>

| POL-001 | Admission policy SHALL be provider independent wherever the rule expresses an architectural invariant. |
| --- | --- |


<a id="source-table-267"></a>

| POL-002 | Provider-specific plan checks SHOULD validate that the adapter compiled the intent into the expected native constructs. |
| --- | --- |

[Previous chapter](31-state-boundaries.md) · [Chapter index](README.md) · [Next chapter](33-secrets-and-automation-credentials.md)
