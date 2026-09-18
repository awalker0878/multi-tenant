# 16. IP Address Management

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:156 BEGIN -->

<!-- SOURCE-BLOCK HB10:156 END -->

<!-- SOURCE-BLOCK HB10:157 BEGIN -->

IPAM is an authoritative service, not a spreadsheet or module default. Terraform requests an allocation and records the resulting prefix; it does not choose arbitrary ranges. Unique addresses are the default because they simplify routing, observability, shared-service consumption, incident response, migration, and cross-platform operation.

<!-- SOURCE-BLOCK HB10:157 END -->

<!-- SOURCE-BLOCK HB10:158 BEGIN -->


<a id="source-table-158"></a>

| Address Authority<br>  └── Region / Site<br>      └── Tenant Namespace<br>          └── Security Domain Instance<br>              └── Workload Network<br>                  ├── IPv4 prefix<br>                  └── IPv6 prefix<br> |
| --- |

<!-- SOURCE-BLOCK HB10:158 END -->

<!-- SOURCE-BLOCK HB10:159 BEGIN -->


<a id="source-table-159"></a>

| IPAM-001 | Every managed network SHALL have an authoritative IPAM record and owner. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:159 END -->

<!-- SOURCE-BLOCK HB10:160 BEGIN -->


<a id="source-table-160"></a>

| IPAM-002 | Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:160 END -->

<!-- SOURCE-BLOCK HB10:161 BEGIN -->


<a id="source-table-161"></a>

| IPAM-003 | Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:161 END -->

[Previous chapter](15-routing-architecture-and-route-authority.md) · [Chapter index](README.md) · [Next chapter](17-ipv6-and-dual-stack.md)
