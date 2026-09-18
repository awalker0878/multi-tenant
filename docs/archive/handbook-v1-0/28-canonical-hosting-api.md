# 28. Canonical Hosting API

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
The portable API is the consumer-facing contract. It is versioned independently of platform modules and expresses desired outcomes. A schema registry validates syntax and semantic compatibility before platform selection.


<a id="source-table-229"></a>

| apiVersion: hosting.platform/v1<br>kind: WorkloadSecurityDomain<br>metadata:<br>  tenant: tenant-001<br>  name: application-prod<br>security:<br>  profile: protected-b-medium<br>  assurance: standard<br>placement:<br>  platform: auto<br>  availability: medium<br>zones:<br>  operations: { enabled: true }<br>  restricted: { enabled: true }<br>networks:<br>  frontend:   { zone: operations,  ipv4PrefixSize: 24, ipv6: true }<br>  database:   { zone: restricted, ipv4PrefixSize: 24, ipv6: true }<br>services:<br>  dns: true<br>  ntp: true<br>  identity: true<br>  logging: true<br>  backup: true<br>flows:<br>  - { source: frontend, destination: database, service: database }<br>exposure:<br>  publicIngress: false<br>  internetEgress: false<br> |
| --- |


<a id="source-table-230"></a>

| API-001 | The portable API SHALL be versioned and backward-compatibility rules SHALL be published. |
| --- | --- |


<a id="source-table-231"></a>

| API-002 | Vendor identifiers, VLAN/VNI/VRF details, route targets, raw firewall rules and raw next-hop routes SHALL NOT be part of the normal consumer contract. |
| --- | --- |

[Previous chapter](33-part-iv-zero-touch-automation-and-terraform.md) · [Chapter index](README.md) · [Next chapter](29-zero-touch-provisioning-workflow.md)
