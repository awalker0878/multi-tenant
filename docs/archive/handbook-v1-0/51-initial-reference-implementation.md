# 51. Initial Reference Implementation

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
The first production-grade proof should stay intentionally small while exercising every major architecture boundary. A useful scope is two tenant namespaces, each with an Operations-zone and Restricted-zone Security Domain, a multi-tenant data ZIP service, separate management/OOB, DNS/NTP/logging/backup service bindings, IPv4 plus an IPv6 test path, and no direct Internet exposure. The goal is to prove the contract and controls, not maximize feature count.


<a id="source-table-394"></a>

| Test Scenario | Expected |
| --- | --- |
| Tenant A workload → Tenant B workload | DENY |
| Operations → Restricted unapproved flow | DENY |
| Restricted → Internet | DENY |
| Workload → management interface | DENY |
| Operations → approved Restricted service | ALLOW |
| Restricted → DNS service binding | ALLOW |
| Restricted → backup data endpoint | ALLOW |
| Security-edge logs attributable to WSD/domain | PASS |
| Provision new WSD without switch configuration | PASS |

[Previous chapter](50-delivery-roadmap.md) · [Chapter index](README.md) · [Next chapter](52-architecture-acceptance-criteria.md)
