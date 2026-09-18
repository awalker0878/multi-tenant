# 2. Normative Language and Architectural Invariants

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:56 BEGIN -->

<!-- SOURCE-BLOCK HB10:56 END -->

<!-- SOURCE-BLOCK HB10:57 BEGIN -->


<a id="source-table-57"></a>

| Term | Meaning |
| --- | --- |
| SHALL / MUST | Mandatory requirement. Any deviation requires a documented exception. |
| SHOULD | Recommended default. A different choice requires documented rationale and equivalent assurance. |
| MAY | Optional implementation choice. |
| Consumer | Person, team, application pipeline, or service catalogue using the hosting service. |
| Provider | The hosting capability and its operations/control plane; not a specific commercial vendor. |

<!-- SOURCE-BLOCK HB10:57 END -->

<!-- SOURCE-BLOCK HB10:58 BEGIN -->

## 2.1 Invariants

<!-- SOURCE-BLOCK HB10:58 END -->

<!-- SOURCE-BLOCK HB10:59 BEGIN -->


<a id="source-table-59"></a>

| INV-001 | Tenant identity, security-zone identity, workload lifecycle, and platform realization are separate concepts. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:59 END -->

<!-- SOURCE-BLOCK HB10:60 BEGIN -->


<a id="source-table-60"></a>

| INV-002 | A VPC, VRF, Tier-1 gateway, or Neutron router is an implementation mechanism, not the enterprise definition of a security zone. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:60 END -->

<!-- SOURCE-BLOCK HB10:61 BEGIN -->


<a id="source-table-61"></a>

| INV-003 | Routes are derived from authorized intent; workload owners do not provide arbitrary route tables, BGP peers, route targets, or prefix imports/exports. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:61 END -->

<!-- SOURCE-BLOCK HB10:62 BEGIN -->


<a id="source-table-62"></a>

| INV-004 | Shared services are exposed through explicit service bindings; broad reachability to a common-services supernet is not the default. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:62 END -->

<!-- SOURCE-BLOCK HB10:63 BEGIN -->


<a id="source-table-63"></a>

| INV-005 | Portability means equivalent required outcomes and conformance, not identical topology. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:63 END -->

<!-- SOURCE-BLOCK HB10:64 BEGIN -->


<a id="source-table-64"></a>

| INV-006 | A deployment is not Service Ready until realized state and security controls are verified. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:64 END -->

<!-- SOURCE-BLOCK HB10:65 BEGIN -->


<a id="source-table-65"></a>

| INV-007 | Failure of an admission or control-plane dependency SHALL fail new changes closed; failure SHALL NOT silently create a security bypass. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:65 END -->

[Previous chapter](1-purpose-scope-and-intended-use.md) · [Chapter index](README.md) · [Next chapter](3-security-standards-context.md)
