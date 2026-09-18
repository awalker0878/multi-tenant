# 46. Migration and Transition Connectivity

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:348 BEGIN -->

<!-- SOURCE-BLOCK HB10:348 END -->

<!-- SOURCE-BLOCK HB10:349 BEGIN -->

Migration should be modeled as a temporary controlled service. A permanent “migration VRF” is avoided because it tends to become an uncontrolled shared path. Migration intent includes source, destination, protocol/service, bandwidth, start, expiry, logging and teardown.

<!-- SOURCE-BLOCK HB10:349 END -->

<!-- SOURCE-BLOCK HB10:350 BEGIN -->


<a id="source-table-350"></a>

| MIG-001 | Migration connectivity SHALL be time-bound unless explicitly converted to an approved steady-state connection. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:350 END -->

<!-- SOURCE-BLOCK HB10:351 BEGIN -->


<a id="source-table-351"></a>

| MIG-002 | Migration flows SHALL traverse an approved security edge when they cross security-domain boundaries. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:351 END -->

<!-- SOURCE-BLOCK HB10:352 BEGIN -->

<!-- SOURCE-BLOCK HB10:352 END -->

[Previous chapter](45-lifecycle-and-offboarding.md) · [Chapter index](README.md) · [Next chapter](54-part-vi-governance-and-delivery.md)
