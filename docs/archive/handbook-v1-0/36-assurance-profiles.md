# 36. Assurance Profiles

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

<a id="source-table-283"></a>

| Profile | Default Isolation | Typical Use |
| --- | --- | --- |
| Standard | Shared physical infrastructure with verified logical isolation, independent tenant/domain policy, mandatory testing | Normal workloads matching the approved baseline context |
| Enhanced | Dedicated routing/security contexts, stronger inspection/telemetry, constrained sharing, additional tests | Higher sensitivity or threat exposure |
| Dedicated | Dedicated or independently assured infrastructure where justified | Exceptional cases requiring physical or strong dedicated separation |

The assurance profile determines realization choices such as shared vs dedicated Security Domain, shared vs dedicated security-edge context, management separation, telemetry, encryption, platform eligibility, test depth, and whether physical controls are required.


<a id="source-table-285"></a>

| ASSUR-001 | Assurance profile selection SHALL be based on system security requirements and risk analysis rather than tenant preference alone. |
| --- | --- |

[Previous chapter](42-part-v-assurance-testing-and-operations.md) · [Chapter index](README.md) · [Next chapter](37-conformance-test-framework.md)
