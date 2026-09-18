# F19  |  Document fencing and pre/post-activation verification explicitly

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:159 BEGIN -->

<!-- SOURCE-BLOCK AUD11:159 END -->

<!-- SOURCE-BLOCK AUD11:160 BEGIN -->

Medium priority • Proposed engineering strengthening<br>Location: Chapters 41, 43 and 46; Figure 4 p37

<!-- SOURCE-BLOCK AUD11:160 END -->

<!-- SOURCE-BLOCK AUD11:161 BEGIN -->

Observed. The handbook already specifies journals, leases, staged apply and incident precedence. It does not fully define stale-runner fencing after lease loss or the test access needed to verify public ingress before the stage that activates exposure.

<!-- SOURCE-BLOCK AUD11:161 END -->

<!-- SOURCE-BLOCK AUD11:162 BEGIN -->

Why it matters. Two controllers or a delayed provider task could act on different generations; pre-activation tests could be impossible without an explicit canary path.

<!-- SOURCE-BLOCK AUD11:162 END -->

<!-- SOURCE-BLOCK AUD11:163 BEGIN -->

Improve. Define fencing tokens or equivalent single-writer guarantees across reservations and actuators, lease-loss behavior and delayed task reconciliation. Separate isolated/canary verification from controlled activation and immediate post-activation checks, with rollback/containment gates.

<!-- SOURCE-BLOCK AUD11:163 END -->

<!-- SOURCE-BLOCK AUD11:164 BEGIN -->

Close when. In an authorized test environment, a stale runner cannot commit after losing authority; ingress is verified without an unrestricted pre-ready window.

<!-- SOURCE-BLOCK AUD11:164 END -->

<!-- SOURCE-BLOCK AUD11:165 BEGIN -->

Owner: Controller and reliability engineering

<!-- SOURCE-BLOCK AUD11:165 END -->

[Previous chapter](20-f18-cadence-and-execution-status-records-need-reconciliation.md) · [Chapter index](README.md) · [Next chapter](22-f20-add-one-end-to-end-service-materialization-contract.md)
