# Appendix H — Normative Requirement Catalogue

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:432 BEGIN -->

<!-- SOURCE-BLOCK HB10:432 END -->

<!-- SOURCE-BLOCK HB10:433 BEGIN -->


<a id="source-table-433"></a>

| Requirement | Summary |
| --- | --- |
| ARCH-001 | Vendor-neutral consumer contract |
| ARCH-002 | No routine switch changes for tenant lifecycle |
| ARCH-003 | Inter-zone paths through ZIP |
| ARCH-004 | Separate management/OOB |
| TEN-001 | Cross-tenant deny by default |
| TEN-002 | Tenant admin cannot modify provider foundations |
| WSD-001 | All managed workloads represented by lifecycle object |
| WSD-002 | No vendor IDs in consumer contract |
| SDI-001 | Only compatible routing/security authority in one domain |
| SDI-002 | Same zone class does not imply reachability |
| ZIP-001 | All inter-zone paths traverse ZIP |
| ZIP-003 | Default deny at inter-zone boundary |
| MGT-001 | No workload-to-management route |
| FAB-001 | Normal tenant lifecycle does not change fabric |
| FAB-002 | Physical VRFs only for true fabric L3 domains |
| RTE-001 | Routes are provider-controlled outputs |
| RTE-002 | No generic transit VRF |
| IPAM-001 | All networks registered in IPAM |
| IPAM-002 | Overlap by exception |
| IPV6-001 | Equivalent IPv4/IPv6 security semantics |
| SVC-001 | No broad shared-service routing |
| ING-001 | No direct public attachment to internal domain |
| EGR-001 | Internet egress deny by default |
| MICRO-001 | East-west deny by default where required |
| SITE-001 | Site-local Security Domains by default |
| PORT-002 | Placement fails rather than downgrade |
| TF-001 | Provider config in root modules |
| TF-002 | Pin/lock provider versions |
| STATE-001 | Separate automation authority domains |
| AUTO-001 | Admission/IPAM failure stops new provisioning |
| TEST-001 | Negative tests mandatory |
| EVID-001 | Evidence binds intent, code, realized state, tests |
| DRIFT-001 | Security drift changes compliance state |
| FAIL-001 | Failure does not create bypass |
| EXC-001 | Exceptions have owner and expiry |
| LIFE-001 | Offboarding removes connectivity and produces evidence |

<!-- SOURCE-BLOCK HB10:433 END -->

[Previous chapter](67-appendix-g-glossary.md) · [Chapter index](README.md) · [Next chapter](69-appendix-i-references.md)
