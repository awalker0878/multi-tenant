# 19. Public Ingress and Internet Egress

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
## 19.1 Public Ingress

Public exposure is requested as a service outcome, not by creating an external interface in the workload network. The public-access implementation typically includes perimeter policy, a PAZ-hosted ingress function such as WAF/reverse proxy/load balancer where appropriate, and an explicit ZIP-controlled path to the internal application zone.


<a id="source-table-174"></a>

| ING-001 | A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network. |
| --- | --- |


<a id="source-table-175"></a>

| ING-002 | Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state. |
| --- | --- |

## 19.2 Internet Egress

Internet egress is also an explicit service. No WSD receives a default Internet route unless its approved exposure/egress profile permits one. Egress may be mediated by proxy, NAT gateway, security edge, or another approved architecture depending on the platform and security profile.


<a id="source-table-178"></a>

| EGR-001 | Internet egress SHALL be deny-by-default and enabled only through an approved egress profile. |
| --- | --- |


<a id="source-table-179"></a>

| EGR-002 | Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible. |
| --- | --- |

[Previous chapter](18-shared-services-and-service-bindings.md) · [Chapter index](README.md) · [Next chapter](20-workload-microsegmentation.md)
