# Implementation and commissioning

Infrastructure work packages and ownership lead. Tool descriptions remain subordinate to the architecture and distinguish source code, local fixtures, native qualification and activation authority.

| Content | How to use it |
| --- | --- |
| [PROV — Cross-stack provisioning and commissioning strategy](provisioning-strategy/README.md) | P0–P6 scopes, commissioning, changes and safe retirement |
| [IK — Implementation delivery kit](delivery-guide/README.md) | Implementation release and handover method |
| [IMP04 — Implementation execution and readback guide](increment-04/README.md) | Actual Increment 04 readback and recovery scope |

These links open the full converted narrative, tables, placeholders, diagrams and cross-references—not a summary of the Word files. Source metadata and originals remain linked in every chapter.

[Architecture / decision / implementation map](code-map.md)

[Method-of-procedure and handover templates](../templates/implementation-mop/README.md)

[Existing executable commissioning procedure](../COMMISSIONING.md)

[Documentation home](../README.md) · [Architecture decisions](../adr/README.md)

## Executable verification extensions

[I08 routed IPv6 packet, shared-service and recovery experiment](routed-ipv6-lab.md) · [Engineering choices and native qualification boundary](../engineering/routed-ipv6-qualification.md). This adds a local packet layer to the existing model and endpoint tests without changing native provisioning resources.

[I09 known Nutanix task-tree readback](nutanix-task-tree-readback.md) adds an optional bounded parent/child profile and linked local HTTPS/recovery campaign. The existing single-task profile remains unchanged.

## Native reference-service commissioning

[Native reference-service commissioning kit](native-reference/README.md) connects actual site inputs, provider-specific build responsibilities, foundation-service interfaces, W14 observation planning, recovery and retirement. It is an unexecuted planning kit; exported worksheets do not grant deployment or operating authority.
