# 41. High Availability and Failure Behaviour

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:313 BEGIN -->

<!-- SOURCE-BLOCK HB10:313 END -->

<!-- SOURCE-BLOCK HB10:314 BEGIN -->


<a id="source-table-314"></a>

| Failure | Expected Behaviour |
| --- | --- |
| Service catalogue unavailable | Existing workloads continue; new requests pause. |
| Security admission unavailable | New security-significant changes fail closed. |
| IPAM unavailable | New address allocation stops; no guessed/manual fallback in automated path. |
| Terraform runner unavailable | Existing data plane continues; changes pause. |
| Security-edge management unavailable | Existing enforcement remains; management alert raised. |
| One security-edge node fails | HA continues enforcement within capacity targets. |
| Central logging unavailable | Enforcement continues; buffering/alerting follows operational profile. |
| Platform control plane unavailable | Existing workload data plane should continue where platform design supports it. |

<!-- SOURCE-BLOCK HB10:314 END -->

<!-- SOURCE-BLOCK HB10:315 BEGIN -->


<a id="source-table-315"></a>

| FAIL-001 | Control-plane failure SHALL NOT create an implicit permit path. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:315 END -->

<!-- SOURCE-BLOCK HB10:316 BEGIN -->


<a id="source-table-316"></a>

| FAIL-002 | Failover and control-plane-loss scenarios SHALL be included in platform conformance testing. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:316 END -->

[Previous chapter](40-capacity-and-performance-engineering.md) · [Chapter index](README.md) · [Next chapter](42-backup-and-restore.md)
