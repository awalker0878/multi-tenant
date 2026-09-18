# 37. Conformance Test Framework

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
A platform is conformant only when it can prove the required outcomes. The conformance suite should run both at platform-certification time and in reduced form for every WSD deployment.


<a id="source-table-288"></a>

| Test Domain | Example Required Outcome |
| --- | --- |
| Tenant isolation | No unauthorized path between independent tenant namespaces. |
| Zone isolation | No inter-zone path except through the declared security edge. |
| Management isolation | Workload cannot reach management/OOB interfaces. |
| Route control | Only authorized prefixes/defaults/peers are present. |
| Microsegmentation | Unapproved east-west traffic fails; approved flow passes. |
| Service bindings | Only declared service endpoints are reachable. |
| Public exposure | Ingress reaches only declared service path. |
| IPv6 | Equivalent negative/positive tests pass. |
| Logging | Security events and flow evidence are centrally attributable. |
| Failure | HA/control-plane failure preserves enforcement. |
| Lifecycle | Modification and deletion remove old connectivity and identity. |


<a id="source-table-289"></a>

| TEST-001 | Negative tests SHALL be first-class acceptance criteria; proving that an allowed flow works is insufficient. |
| --- | --- |


<a id="source-table-290"></a>

| TEST-002 | A platform upgrade SHALL trigger an appropriate regression/conformance test set before broad production rollout. |
| --- | --- |

[Previous chapter](36-assurance-profiles.md) · [Chapter index](README.md) · [Next chapter](38-deployment-evidence.md)
