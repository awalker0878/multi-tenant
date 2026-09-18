# 24. VMware / NSX Implementation Profile

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
The complete portable networking/security profile requires NSX or an equivalent SDN/security layer; plain vSphere networking alone should not be assumed to provide the same tenant and policy semantics. NSX projects, Tier-1 contexts, segments, distributed security policy and gateway policy can be mapped to the portable model.


<a id="source-table-210"></a>

| Portable Concept | NSX Realization |
| --- | --- |
| Tenant Namespace | NSX Project / IAM mapping |
| Security Domain Instance | Project-scoped Tier-1 / routing context |
| Workload Network | Segment |
| Microsegmentation | Distributed Security Policy |
| Zone edge | Gateway Policy / Edge services |
| Metadata | Tags / Groups |
| Workload placement | vSphere compute + NSX network context |


<a id="source-table-211"></a>

| NSX-001 | An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy. |
| --- | --- |


<a id="source-table-212"></a>

| NSX-002 | Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload. |
| --- | --- |

[Previous chapter](23-nutanix-implementation-profile.md) · [Chapter index](README.md) · [Next chapter](25-openstack-implementation-profile.md)
