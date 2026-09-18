# 40. Capacity and Performance Engineering

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:300 BEGIN -->

<!-- SOURCE-BLOCK HB10:300 END -->

<!-- SOURCE-BLOCK HB10:301 BEGIN -->

The security edge and shared-service layer become critical infrastructure. Capacity must be engineered so that security controls are not viewed as optional bottlenecks during growth or incidents.

<!-- SOURCE-BLOCK HB10:301 END -->

<!-- SOURCE-BLOCK HB10:302 BEGIN -->

- Aggregate and per-context throughput

<!-- SOURCE-BLOCK HB10:302 END -->

<!-- SOURCE-BLOCK HB10:303 BEGIN -->

- Concurrent sessions and new sessions per second

<!-- SOURCE-BLOCK HB10:303 END -->

<!-- SOURCE-BLOCK HB10:304 BEGIN -->

- Packet-per-second capacity and latency

<!-- SOURCE-BLOCK HB10:304 END -->

<!-- SOURCE-BLOCK HB10:305 BEGIN -->

- Inspection/TLS processing where applicable

<!-- SOURCE-BLOCK HB10:305 END -->

<!-- SOURCE-BLOCK HB10:306 BEGIN -->

- Log/event throughput and storage

<!-- SOURCE-BLOCK HB10:306 END -->

<!-- SOURCE-BLOCK HB10:307 BEGIN -->

- HA failover headroom

<!-- SOURCE-BLOCK HB10:307 END -->

<!-- SOURCE-BLOCK HB10:308 BEGIN -->

- Per-tenant noisy-neighbour limits

<!-- SOURCE-BLOCK HB10:308 END -->

<!-- SOURCE-BLOCK HB10:309 BEGIN -->

- Route and policy object scale

<!-- SOURCE-BLOCK HB10:309 END -->

<!-- SOURCE-BLOCK HB10:310 BEGIN -->

- Platform VPC/Tier-1/router/network scale

<!-- SOURCE-BLOCK HB10:310 END -->

<!-- SOURCE-BLOCK HB10:311 BEGIN -->

- Automation concurrency and provider API limits

<!-- SOURCE-BLOCK HB10:311 END -->

<!-- SOURCE-BLOCK HB10:312 BEGIN -->


<a id="source-table-312"></a>

| CAP-001 | Capacity planning SHALL include N+failure headroom so that loss of a security-edge node does not require disabling or bypassing enforcement. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:312 END -->

[Previous chapter](39-logging-telemetry-and-observability.md) · [Chapter index](README.md) · [Next chapter](41-high-availability-and-failure-behaviour.md)
