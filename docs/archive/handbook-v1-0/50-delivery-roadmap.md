# 50. Delivery Roadmap

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:390 BEGIN -->

<!-- SOURCE-BLOCK HB10:390 END -->

<!-- SOURCE-BLOCK HB10:391 BEGIN -->


<a id="source-table-391"></a>

| Phase | Primary Deliverables | Exit Gate |
| --- | --- | --- |
| 1 — Standard | Portable contract, terminology, invariants, zone/ZIP model, assurance profiles | Architecture and security approval of the vendor-neutral model |
| 2 — Physical foundation | L3 Clos, OOB, platform/security-edge attachment patterns | Tenant creation proven without routine switch change |
| 3 — Security edge &amp; services | Data ZIP, management ZIP, ingress/egress, service endpoints | Explicit inter-zone/service paths operational |
| 4 — First platform profile | Platform adapter, native modules, baseline policies | One complete WSD provisioned zero-touch |
| 5 — Assurance automation | Admission, IPAM, route authority, tests, evidence | Service Ready blocked unless mandatory tests pass |
| 6 — Additional platforms | Second and third implementation profiles | Same WSD contract passes conformance on multiple platforms |
| 7 — Policy-driven placement | Capability registry and platform:auto | Authorized placement selected without consumer vendor dependency |
| 8 — Continuous authorization | Drift, evidence, exceptions, lifecycle automation | Ongoing compliance state visible and actionable |

<!-- SOURCE-BLOCK HB10:391 END -->

[Previous chapter](49-tenant-wsd-onboarding-checklist.md) · [Chapter index](README.md) · [Next chapter](51-initial-reference-implementation.md)
