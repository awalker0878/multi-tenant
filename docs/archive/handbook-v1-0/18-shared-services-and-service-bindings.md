# 18. Shared Services and Service Bindings

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Shared infrastructure functions such as DNS, NTP, identity, PKI, logging, monitoring, backup and KMS should be published as service endpoints rather than broad routable networks. A Service Binding is an explicit relationship between a consumer Security Domain and an approved service endpoint.


<a id="source-table-168"></a>

| Service Binding Field | Example |
| --- | --- |
| Service identity | dns-resolver / ntp / identity / logging / backup |
| Consumer domain | Restricted-zone instance for workload X |
| Endpoint | Virtual IP, service address, proxy, gateway or service-specific attachment |
| Allowed direction | Consumer-to-service, service-to-consumer, or controlled bidirectional |
| Protocol/port | Derived from service profile |
| Logging | Mandatory / sampled / service-specific |
| Availability | Local, redundant, multi-site, or service-defined |
| Evidence | Reachability test + policy/config references |


<a id="source-table-169"></a>

| SVC-001 | Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service. |
| --- | --- |


<a id="source-table-170"></a>

| SVC-002 | Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing. |
| --- | --- |

[Previous chapter](17-ipv6-and-dual-stack.md) · [Chapter index](README.md) · [Next chapter](19-public-ingress-and-internet-egress.md)
