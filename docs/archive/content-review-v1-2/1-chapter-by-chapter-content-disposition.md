# 1. Chapter-by-chapter content disposition

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Content_Review_v1_2.docx) · [Chapter index](README.md)

> **Source:** REV12 — Review of the 45-page v1.2 editorial branch. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8ddf5ff71f4779a15e56ed3708ace1f8315116ed1e6c9ce1f6a73276d7101a89 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK REV12:11 BEGIN -->

<!-- SOURCE-BLOCK REV12:11 END -->

<!-- SOURCE-BLOCK REV12:12 BEGIN -->

## Prior chapters 1–10

<!-- SOURCE-BLOCK REV12:12 END -->

<!-- SOURCE-BLOCK REV12:13 BEGIN -->


<a id="source-table-13"></a>

| v1.1 source chapter | Disposition / destination | Review decision |
| --- | --- | --- |
| 1. Purpose, scope and release boundaries | Rewritten; v1.2 1 | Scope now describes infrastructure and provisioning, not a typed service application. |
| 2. Normative language, invariants and authority | Consolidated; v1.2 3, 26 | Architecture decisions and acceptance replace repeated normative/catalogue machinery. |
| 3. Standards hierarchy and the 2026 baseline | Retained / focused; v1.2 3; Appendix B | Applicable source hierarchy remains; detailed catalogue migration mechanics are not main narrative. |
| 4. Categorization and policy profiles | Retained / reframed; v1.2 3, 9, 25 | Security and service requirements remain independent; typed profile objects are not mandated. |
| 5. Threat model and trust boundaries | Integrated; v1.2 3–14, 23, 26 | Threat and failure responses appear at the actual infrastructure boundaries. |
| 6. Canonical model and service planes | Rewritten; v1.2 2, 9 | Target components and domain meanings replace a canonical application object model. |
| 7. Tenant Namespace, entitlements and ownership | Retained / reframed; v1.2 9, 21 | Administrative ownership, entitlement and lifecycle remain; serialization details removed. |
| 8. WSD intent and lifecycle responsibility | Retained / reframed; v1.2 9, 21, 24 | WSD is a bounded hosting environment, not primarily a controller object. |
| 9. Security Domains and site/platform instances | Retained / expanded; v1.2 9, 15–18 | Logical authority and site/platform realization remain distinct. |
| 10. Zone classes, external domains and adjacency | Retained / clarified; v1.2 10 | External authority retained; HRZ eligibility caveat made explicit for portable cloud scope. |

<!-- SOURCE-BLOCK REV12:13 END -->

<!-- SOURCE-BLOCK REV12:14 BEGIN -->

<!-- SOURCE-BLOCK REV12:14 END -->

<!-- SOURCE-BLOCK REV12:15 BEGIN -->

## Prior chapters 11–21

<!-- SOURCE-BLOCK REV12:15 END -->

<!-- SOURCE-BLOCK REV12:16 BEGIN -->


<a id="source-table-16"></a>

| v1.1 source chapter | Disposition / destination | Review decision |
| --- | --- | --- |
| 11. ZIP architecture and joint boundary authority | Retained / expanded; v1.2 10–12 | ZIP authority, physical/logical enforcement and alternatives are grounded in packet paths. |
| 12. MZ, OOB and privileged management access | Retained / expanded; v1.2 6 | MZ, OOB, native administration and tenant guest access are distinct. |
| 13. Platform overlays and enforcement ownership | Retained / expanded; v1.2 5, 11, 15–18 | Overlay ownership is tied to actual native routing and attachment designs. |
| 14. Route Authority and safe forwarding compilation | Reframed; v1.2 5, 11 | Route authority is an infrastructure responsibility, not a required custom compiler application. |
| 15. IPAM, DNS and DHCP as one lifecycle | Consolidated; v1.2 5, 8, 12, 20–23 | Authoritative allocation and DNS/DHCP lifecycle retained; API transaction details excluded. |
| 16. IPv6 and alternate-path control | Retained / clarified; v1.2 12, 26 | Address-family completeness retained without relying on the inconsistent old schema. |
| 17. Shared services and explicit Service Bindings | Retained / expanded; v1.2 8, 12 | Service placement, initiation direction and administration paths are explicit. |
| 18. Public ingress, controlled egress and external exposure | Retained / expanded; v1.2 10–12, 21 | Ingress/egress is explained as a network/service path and activation responsibility. |
| 19. Microsegmentation, labels and workload attachment | Retained / integrated; v1.2 9, 12, 15–17 | Same-host isolation and protected selectors are placed in the native stack designs. |
| 20. Provider-internal Edge Attachment contract | Rewritten; v1.2 11, 15–18 | Physical/logical handoff patterns replace a field-level EdgeAttachment contract. |
| 21. Multi-site domains and recovery connectivity | Retained / expanded; v1.2 4, 14 | Site-local dependencies, replication, recovery and fencing shown as infrastructure. |

<!-- SOURCE-BLOCK REV12:16 END -->

<!-- SOURCE-BLOCK REV12:17 BEGIN -->

<!-- SOURCE-BLOCK REV12:17 END -->

<!-- SOURCE-BLOCK REV12:18 BEGIN -->

## Prior chapters 22–31

<!-- SOURCE-BLOCK REV12:18 END -->

<!-- SOURCE-BLOCK REV12:19 BEGIN -->


<a id="source-table-19"></a>

| v1.1 source chapter | Disposition / destination | Review decision |
| --- | --- | --- |
| 22. Compute, hypervisor security and co-residency | Retained / clarified; v1.2 7, 15–17 | Per-layer sharing and actual host-pool boundaries retained. |
| 23. Storage, data services and copy lineage | Retained / focused; v1.2 7, 13, 18 | Storage access, performance, copy/retention and exit retained without a storage object schema. |
| 24. Identity, privileged access and service identities | Retained / integrated; v1.2 6, 8, 13 | Human, service and automation authority are shown at consumption/management boundaries. |
| 25. Cryptography, KMS, certificates and crypto agility | Retained / focused; v1.2 13 | Key custody, encryption and loss/recovery remain; software profile details excluded. |
| 26. Images, configuration baselines and endpoint protection | Retained / integrated; v1.2 7, 19, 21, 25 | Approved images and configuration ownership remain; build application internals excluded. |
| 27. Backup, retention and isolated restore | Retained / integrated; v1.2 8, 13, 14, 23 | Backup data/control paths, independent protection and isolated restore retained. |
| 28. Availability and recovery service profiles | Retained / integrated; v1.2 3, 14, 25 | SLO/RTO/RPO remain measured service requirements; no arbitrary default claims. |
| 29. Placement, data location and sovereign optionality | Retained / integrated; v1.2 13–14, 18, 26 | Placement, permitted locations, support paths and exit are infrastructure constraints. |
| 30. Service catalogue, quotas and capacity on demand | Retained / integrated; v1.2 1, 19, 21, 25 | Capacity-on-demand and inventory distinctions remain; catalogue application design excluded. |
| 31. Application responsibilities and end-to-end service readiness | Reduced to interface; v1.2 1, 13, 21, 25 | Application design removed; guest/data-owner handover and acceptance responsibilities retained. |

<!-- SOURCE-BLOCK REV12:19 END -->

<!-- SOURCE-BLOCK REV12:20 BEGIN -->

<!-- SOURCE-BLOCK REV12:20 END -->

<!-- SOURCE-BLOCK REV12:21 BEGIN -->

## Prior chapters 32–38

<!-- SOURCE-BLOCK REV12:21 END -->

<!-- SOURCE-BLOCK REV12:22 BEGIN -->


<a id="source-table-22"></a>

| v1.1 source chapter | Disposition / destination | Review decision |
| --- | --- | --- |
| 32. Physical fabric foundation and commissioning | Retained / expanded; v1.2 4–5, 20 | Physical topology and ordered commissioning made central. |
| 33. EVPN/VXLAN, multihoming and border engineering | Retained / expanded; v1.2 5 | Underlay, EVPN, route imports, multihoming and border ownership retained. |
| 34. Portability dimensions and platform qualification | Retained / reframed; v1.2 18, 26 | Outcome equivalence and qualification retained; capability-object state machine excluded. |
| 35. Nutanix implementation profile | Expanded; v1.2 15, 22 | Nutanix components, traffic, ownership, sequence and implementation limits added. |
| 36. VMware and NSX implementation profile | Expanded; v1.2 16, 22 | VMware/NSX native path, upstream isolation and separate provisioning scopes added. |
| 37. OpenStack implementation profile | Expanded; v1.2 17, 22 | OpenStack backend, project/router/port authority and foundation/provider distinction added. |
| 38. Bare metal, containers and future platforms | Scope reduced; v1.2 11, 18, 26 | Fabric-routed physical extension retained. Detailed container platform design deferred to its own qualified profile. |

<!-- SOURCE-BLOCK REV12:22 END -->

<!-- SOURCE-BLOCK REV12:23 BEGIN -->

<!-- SOURCE-BLOCK REV12:23 END -->

<!-- SOURCE-BLOCK REV12:24 BEGIN -->

## Prior chapters 39–46

<!-- SOURCE-BLOCK REV12:24 END -->

<!-- SOURCE-BLOCK REV12:25 BEGIN -->


<a id="source-table-25"></a>

| v1.1 source chapter | Disposition / destination | Review decision |
| --- | --- | --- |
| 39. Canonical API, object ownership and status | Removed from main; v1.2 1, 18, 22 | HTTP/API/schema/status/concurrency design is not the infrastructure architecture; common service needs remain. |
| 40. Admission, Flow Intention and policy compilation | Reframed; v1.2 10–12, 21–22 | Allowed flows, effective policy and approval remain; compiler implementation is not prescribed. |
| 41. Zero-touch provisioning and reconciliation workflow | Rewritten; v1.2 19–23 | Infrastructure dependency and lifecycle sequence replaces custom controller workflow. |
| 42. Terraform roots, adapters and reproducible inputs | Reduced / reframed; v1.2 19, 22 | Actual provider scopes and ownership retained; HCL examples and repository tree removed. |
| 43. State boundaries, cross-state transactions and partial failure | Reduced / reframed; v1.2 22–23 | Separate authority/state, handoffs and partial-operation safety retained; software saga design removed. |
| 44. CI/CD, signed plans and supply-chain integrity | Reduced / reframed; v1.2 19, 22–23, 25 | Trusted changes and supply-chain responsibilities retained; detailed pipeline/signature implementation excluded. |
| 45. Secrets and automation credentials | Reduced / integrated; v1.2 6, 13, 22 | Credential/state protection retained at architectural level; ephemeral syntax examples removed. |
| 46. Drift, emergency overrides and desired-state convergence | Retained / reframed; v1.2 23, 25 | Actual-state comparison and incident precedence retained; controller object lifecycle excluded. |

<!-- SOURCE-BLOCK REV12:25 END -->

<!-- SOURCE-BLOCK REV12:26 BEGIN -->

<!-- SOURCE-BLOCK REV12:26 END -->

<!-- SOURCE-BLOCK REV12:27 BEGIN -->

## Prior chapters 47–57

<!-- SOURCE-BLOCK REV12:27 END -->

<!-- SOURCE-BLOCK REV12:28 BEGIN -->


<a id="source-table-28"></a>

| v1.1 source chapter | Disposition / destination | Review decision |
| --- | --- | --- |
| 47. Assurance profiles and isolation decisions | Reframed; v1.2 3, 7, 26 | Explicit sharing and dedication decisions replace descriptive software profile levels. |
| 48. Conformance framework and test execution | Condensed to acceptance; v1.2 26 | Required verification outcomes retained; 80 procedural test specifications are outside the main narrative. |
| 49. Evidence, controls and authorization records | Reduced to assurance boundary; v1.2 25–26 | Attributable evidence and separate authorization remain; evidence application schema removed. |
| 50. Logging, telemetry and time integrity | Retained / integrated; v1.2 8, 12, 25 | Telemetry placement, attribution, protection and operational dependencies retained. |
| 51. Capacity, performance and capacity-on-demand operations | Retained / integrated; v1.2 4–5, 19, 25 | Capacity and procurement/consumption differences tied to foundation and service lifecycle. |
| 52. High availability and dependency failure behavior | Retained / integrated; v1.2 14, 23, 25 | Dependency failure behaviour tied to infrastructure; no implicit permit fallback. |
| 53. Recovery, bootstrap and failback runbooks | Reframed; v1.2 14, 20, 23 | Recovery dependency order retained; detailed operator record/runbook fields excluded. |
| 54. Vulnerability, patch and support lifecycle | Retained / integrated; v1.2 19–20, 23, 25 | Native lifecycle, supported inventory and controlled upgrades retained. |
| 55. Incident response and scoped containment | Retained / integrated; v1.2 23, 25 | Scoped containment and evidence preservation retained; incident application object removed. |
| 56. Lifecycle, retirement and secure disposal | Retained / integrated; v1.2 13, 23 | Data-aware infrastructure retirement retained; software finalizer details removed. |
| 57. Migration, portability and exit rehearsal | Retained / integrated; v1.2 14, 18, 23–24 | Rebuild/data-transfer/exit boundaries retained without pretending Terraform migrates data. |

<!-- SOURCE-BLOCK REV12:28 END -->

<!-- SOURCE-BLOCK REV12:29 BEGIN -->

<!-- SOURCE-BLOCK REV12:29 END -->

<!-- SOURCE-BLOCK REV12:30 BEGIN -->

## Prior chapters 58–62

<!-- SOURCE-BLOCK REV12:30 END -->

<!-- SOURCE-BLOCK REV12:31 BEGIN -->


<a id="source-table-31"></a>

| v1.1 source chapter | Disposition / destination | Review decision |
| --- | --- | --- |
| 58. Operating model and separation of duties | Retained / refocused; v1.2 19, 25 | Infrastructure and service accountability remain; custom-controller operating team not prescribed. |
| 59. Change, exceptions and risk decisions | Retained / integrated; v1.2 3, 23, 26 | Change/risk authority retained; exception serialization/state machine excluded. |
| 60. Architecture review and onboarding gates | Rewritten; v1.2 20–21, 26 | Commissioning, tenant/WSD and activation gates are concrete infrastructure stages. |
| 61. Delivery roadmap and reference implementation | Rewritten; v1.2 20, 24, 26 | First-platform then multi-platform delivery, without custom application prerequisite. |
| 62. Architecture acceptance and document release | Rewritten; v1.2 26 | Architectural and operational acceptance replaces document/contract completeness claims. |

<!-- SOURCE-BLOCK REV12:31 END -->

<!-- SOURCE-BLOCK REV12:32 BEGIN -->

<!-- SOURCE-BLOCK REV12:32 END -->

[Chapter index](README.md) · [Next chapter](2-appendix-disposition.md)
