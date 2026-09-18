# 34. CI/CD and Change Gates

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:273 BEGIN -->

<!-- SOURCE-BLOCK HB10:273 END -->

<!-- SOURCE-BLOCK HB10:274 BEGIN -->


<a id="source-table-274"></a>

| Stage | Mandatory Controls |
| --- | --- |
| Commit | Peer review, lint, schema tests, unit tests, secret scanning |
| Plan | Pinned providers/modules, policy checks, drift awareness, change classification |
| Approval | Risk-based approval; stronger approval for security edge, management, external exposure |
| Apply | Least-privileged identity, serialized/locked state, auditable execution |
| Realization | Wait for platform readiness |
| Verification | Connectivity/security/logging tests |
| Evidence | Immutable/tamper-evident record and deployment provenance |

<!-- SOURCE-BLOCK HB10:274 END -->

<!-- SOURCE-BLOCK HB10:275 BEGIN -->


<a id="source-table-275"></a>

| CICD-001 | A change that modifies inter-zone policy, external exposure, route authority, management access, or assurance profile SHALL receive a higher change classification than an ordinary workload scale operation. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:275 END -->

[Previous chapter](33-secrets-and-automation-credentials.md) · [Chapter index](README.md) · [Next chapter](35-drift-and-reconciliation.md)
