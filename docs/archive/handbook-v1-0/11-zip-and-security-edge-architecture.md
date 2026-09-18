# 11. ZIP and Security Edge Architecture

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:115 BEGIN -->

<!-- SOURCE-BLOCK HB10:115 END -->

<!-- SOURCE-BLOCK HB10:116 BEGIN -->

The ZIP/security edge is the only default place where inter-zone routing is established. It combines routing context, stateful policy, inspection where required, logging, telemetry, management separation, and evidence. A generic transit VRF is not used as an alternate path between zones.

<!-- SOURCE-BLOCK HB10:116 END -->

<!-- SOURCE-BLOCK HB10:117 BEGIN -->


<a id="source-table-117"></a>

| ZIP-001 | All inter-zone network paths SHALL traverse the applicable ZIP/security edge. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:117 END -->

<!-- SOURCE-BLOCK HB10:118 BEGIN -->


<a id="source-table-118"></a>

| ZIP-002 | A ZIP SHALL identify both adjacent Security Domain Instances and SHALL NOT serve as a general-purpose third-zone transit domain. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:118 END -->

<!-- SOURCE-BLOCK HB10:119 BEGIN -->


<a id="source-table-119"></a>

| ZIP-003 | Default inter-zone policy SHALL be deny; allowed flows SHALL be generated from approved Flow Intentions and Service Bindings. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:119 END -->

<!-- SOURCE-BLOCK HB10:120 BEGIN -->


<a id="source-table-120"></a>

| ZIP-004 | ZIP management traffic SHALL be segregated from operational traffic. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:120 END -->

<!-- SOURCE-BLOCK HB10:121 BEGIN -->


<a id="source-table-121"></a>

| ZIP-005 | Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services; shared virtualization SHALL only be used where the applicable assurance analysis supports it. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:121 END -->

<!-- SOURCE-BLOCK HB10:122 BEGIN -->

## 11.1 Multi-Tenant Security Edge

<!-- SOURCE-BLOCK HB10:122 END -->

<!-- SOURCE-BLOCK HB10:123 BEGIN -->

Shared security infrastructure may host multiple logical ZIP contexts. The sharing boundary is the infrastructure, not the routing/policy context. Each logical ZIP retains independent interfaces/VRFs or equivalent contexts, policy objects, logs, ownership, configuration and evidence.

<!-- SOURCE-BLOCK HB10:123 END -->

<!-- SOURCE-BLOCK HB10:124 BEGIN -->


<a id="source-table-124"></a>

| Shared Component | Must Remain Isolated Per ZIP |
| --- | --- |
| Physical firewall/security cluster | Routing context / tenant virtual system or equivalent |
| Compute capacity | Policy objects and rule namespace |
| Logging transport | Log identity, tenant/context attribution, access controls |
| Management platform | RBAC scope and change authority |
| HA platform | Configuration and evidence state |

<!-- SOURCE-BLOCK HB10:124 END -->

[Previous chapter](10-security-zone-semantics.md) · [Chapter index](README.md) · [Next chapter](12-management-and-out-of-band-architecture.md)
