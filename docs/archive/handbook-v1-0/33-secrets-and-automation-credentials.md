# 33. Secrets and Automation Credentials

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Terraform configuration, state, CI logs and plan output can expose sensitive values. Credentials should be short-lived or externally brokered where supported. Secrets must not be stored in source repositories. Access to state and plan artifacts must reflect their sensitivity.


<a id="source-table-270"></a>

| SEC-001 | Static privileged provider credentials SHALL NOT be embedded in Terraform source code. |
| --- | --- |


<a id="source-table-271"></a>

| SEC-002 | Automation identities SHALL use least privilege and separate duties by control domain. |
| --- | --- |


<a id="source-table-272"></a>

| SEC-003 | Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile. |
| --- | --- |

[Previous chapter](32-policy-as-code-and-security-admission.md) · [Chapter index](README.md) · [Next chapter](34-ci-cd-and-change-gates.md)
