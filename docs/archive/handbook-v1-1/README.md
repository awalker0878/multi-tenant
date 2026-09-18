# Expanded secure-hosting handbook

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

## Chapters

- [Part I — Foundations and governance context](01-part-i-foundations-and-governance-context.md)
- [1. Purpose, scope and release boundaries](1-purpose-scope-and-release-boundaries.md)
- [2. Normative language, invariants and authority](2-normative-language-invariants-and-authority.md)
- [3. Standards hierarchy and the 2026 baseline](3-standards-hierarchy-and-the-2026-baseline.md)
- [4. Categorization and policy profiles](4-categorization-and-policy-profiles.md)
- [5. Threat model and trust boundaries](5-threat-model-and-trust-boundaries.md)
- [6. Canonical model and service planes](6-canonical-model-and-service-planes.md)
- [Part II — Portable security architecture](08-part-ii-portable-security-architecture.md)
- [7. Tenant Namespace, entitlements and ownership](7-tenant-namespace-entitlements-and-ownership.md)
- [8. WSD intent and lifecycle responsibility](8-wsd-intent-and-lifecycle-responsibility.md)
- [9. Security Domains and site/platform instances](9-security-domains-and-site-platform-instances.md)
- [10. Zone classes, external domains and adjacency](10-zone-classes-external-domains-and-adjacency.md)
- [11. ZIP architecture and joint boundary authority](11-zip-architecture-and-joint-boundary-authority.md)
- [12. MZ, OOB and privileged management access](12-mz-oob-and-privileged-management-access.md)
- [13. Platform overlays and enforcement ownership](13-platform-overlays-and-enforcement-ownership.md)
- [14. Route Authority and safe forwarding compilation](14-route-authority-and-safe-forwarding-compilation.md)
- [15. IPAM, DNS and DHCP as one lifecycle](15-ipam-dns-and-dhcp-as-one-lifecycle.md)
- [16. IPv6 and alternate-path control](16-ipv6-and-alternate-path-control.md)
- [17. Shared services and explicit Service Bindings](17-shared-services-and-explicit-service-bindings.md)
- [18. Public ingress, controlled egress and external exposure](18-public-ingress-controlled-egress-and-external-exposure.md)
- [19. Microsegmentation, labels and workload attachment](19-microsegmentation-labels-and-workload-attachment.md)
- [20. Provider-internal Edge Attachment contract](20-provider-internal-edge-attachment-contract.md)
- [21. Multi-site domains and recovery connectivity](21-multi-site-domains-and-recovery-connectivity.md)
- [Part III — Portable hosting services](24-part-iii-portable-hosting-services.md)
- [22. Compute, hypervisor security and co-residency](22-compute-hypervisor-security-and-co-residency.md)
- [23. Storage, data services and copy lineage](23-storage-data-services-and-copy-lineage.md)
- [24. Identity, privileged access and service identities](24-identity-privileged-access-and-service-identities.md)
- [25. Cryptography, KMS, certificates and crypto agility](25-cryptography-kms-certificates-and-crypto-agility.md)
- [26. Images, configuration baselines and endpoint protection](26-images-configuration-baselines-and-endpoint-protection.md)
- [27. Backup, retention and isolated restore](27-backup-retention-and-isolated-restore.md)
- [28. Availability and recovery service profiles](28-availability-and-recovery-service-profiles.md)
- [29. Placement, data location and sovereign optionality](29-placement-data-location-and-sovereign-optionality.md)
- [30. Service catalogue, quotas and capacity on demand](30-service-catalogue-quotas-and-capacity-on-demand.md)
- [31. Application responsibilities and end-to-end service readiness](31-application-responsibilities-and-end-to-end-service-readiness.md)
- [Part IV — Infrastructure and platform realization](35-part-iv-infrastructure-and-platform-realization.md)
- [32. Physical fabric foundation and commissioning](32-physical-fabric-foundation-and-commissioning.md)
- [33. EVPN/VXLAN, multihoming and border engineering](33-evpn-vxlan-multihoming-and-border-engineering.md)
- [34. Portability dimensions and platform qualification](34-portability-dimensions-and-platform-qualification.md)
- [35. Nutanix implementation profile](35-nutanix-implementation-profile.md)
- [36. VMware and NSX implementation profile](36-vmware-and-nsx-implementation-profile.md)
- [37. OpenStack implementation profile](37-openstack-implementation-profile.md)
- [38. Bare metal, containers and future platforms](38-bare-metal-containers-and-future-platforms.md)
- [Part V — Service control plane and automation](43-part-v-service-control-plane-and-automation.md)
- [39. Canonical API, object ownership and status](39-canonical-api-object-ownership-and-status.md)
- [40. Admission, Flow Intention and policy compilation](40-admission-flow-intention-and-policy-compilation.md)
- [41. Zero-touch provisioning and reconciliation workflow](41-zero-touch-provisioning-and-reconciliation-workflow.md)
- [42. Terraform roots, adapters and reproducible inputs](42-terraform-roots-adapters-and-reproducible-inputs.md)
- [43. State boundaries, cross-state transactions and partial failure](43-state-boundaries-cross-state-transactions-and-partial-failure.md)
- [44. CI/CD, signed plans and supply-chain integrity](44-ci-cd-signed-plans-and-supply-chain-integrity.md)
- [45. Secrets and automation credentials](45-secrets-and-automation-credentials.md)
- [46. Drift, emergency overrides and desired-state convergence](46-drift-emergency-overrides-and-desired-state-convergence.md)
- [Part VI — Assurance and operations](52-part-vi-assurance-and-operations.md)
- [47. Assurance profiles and isolation decisions](47-assurance-profiles-and-isolation-decisions.md)
- [48. Conformance framework and test execution](48-conformance-framework-and-test-execution.md)
- [49. Evidence, controls and authorization records](49-evidence-controls-and-authorization-records.md)
- [50. Logging, telemetry and time integrity](50-logging-telemetry-and-time-integrity.md)
- [51. Capacity, performance and capacity-on-demand operations](51-capacity-performance-and-capacity-on-demand-operations.md)
- [52. High availability and dependency failure behavior](52-high-availability-and-dependency-failure-behavior.md)
- [53. Recovery, bootstrap and failback runbooks](53-recovery-bootstrap-and-failback-runbooks.md)
- [54. Vulnerability, patch and support lifecycle](54-vulnerability-patch-and-support-lifecycle.md)
- [55. Incident response and scoped containment](55-incident-response-and-scoped-containment.md)
- [56. Lifecycle, retirement and secure disposal](56-lifecycle-retirement-and-secure-disposal.md)
- [57. Migration, portability and exit rehearsal](57-migration-portability-and-exit-rehearsal.md)
- [Part VII — Governance and delivery](64-part-vii-governance-and-delivery.md)
- [58. Operating model and separation of duties](58-operating-model-and-separation-of-duties.md)
- [59. Change, exceptions and risk decisions](59-change-exceptions-and-risk-decisions.md)
- [60. Architecture review and onboarding gates](60-architecture-review-and-onboarding-gates.md)
- [61. Delivery roadmap and reference implementation](61-delivery-roadmap-and-reference-implementation.md)
- [62. Architecture acceptance and document release](62-architecture-acceptance-and-document-release.md)
- [Appendix A — Canonical object contract and API surface](70-appendix-a-canonical-object-contract-and-api-surface.md)
- [Appendix B — Worked requests and Terraform execution boundary](71-appendix-b-worked-requests-and-terraform-execution-boundary.md)
- [Appendix C — Complete normative requirement and verification index](72-appendix-c-complete-normative-requirement-and-verification-index.md)
- [Appendix D — Conformance test catalogue](73-appendix-d-conformance-test-catalogue.md)
- [Appendix E — Source/control traceability and responsibility](74-appendix-e-source-control-traceability-and-responsibility.md)
- [Appendix F — Proposed local engineering parameters](75-appendix-f-proposed-local-engineering-parameters.md)
- [Appendix G — Operational records and decision templates](76-appendix-g-operational-records-and-decision-templates.md)
- [Appendix H — Primary sources and implementation references](77-appendix-h-primary-sources-and-implementation-references.md)
- [Appendix I — Glossary](78-appendix-i-glossary.md)
- [Appendix J — Audit closure, migration and release checks](79-appendix-j-audit-closure-migration-and-release-checks.md)

## Source front matter
ARCHITECTURE STANDARD + ENGINEERING HANDBOOK

## Portable<br>Multi-Tenant<br>Secure Hosting

*Complete architecture baseline<br>and zero-touch service contract*

Draft v1.1  \|  16 September 2026

Security outcomes that survive platform change.

A vendor-neutral model for workload intent, controlled trust transitions, protected hosting services, scoped automation, measured recovery and attributable evidence.


<a id="source-table-6"></a>

| 62 chapters | 194 requirements | 80 conformance procedures |
| --- | --- | --- |
| Seven architecture parts | All 99 original IDs mapped | 33 typed contract objects |

DOCUMENT BASELINE COMPLETE • IMPLEMENTATION QUALIFICATION SEPARATE

This release defines and validates the reference documentation and contract package. Live platform qualification, tailored control assessment, site parameters and formal authorization remain implementation responsibilities. Candidate examples and unexecuted tests are explicitly identified.

Document control and how to use this release


<a id="source-table-11"></a>

| Field | Release record |
| --- | --- |
| Title / version | Portable Multi-Tenant Secure Hosting Handbook / Draft v1.1 |
| Status | Completed reference-architecture baseline for adoption, qualification and authorization workflows |
| Source baseline | Uploaded Draft v1.0, 43 pages; all original sections and 99 requirement IDs accounted for |
| Audience | Architecture, security assessment, network/platform/storage/identity engineering, automation, operations and service/data owners |
| Normative authority | SHALL/SHOULD/MAY identify this proposed handbook baseline; adoption and higher-authority applicability are separate decisions |
| Research baseline | Primary references reviewed 16 September 2026; important 2026 control-catalogue and cryptography updates recorded |
| Companion package | Closed schemas, examples, generated requirements/tests/sources, audit/migration records, offline validator and editable diagrams |
| Release limits | No actual infrastructure conformance execution, provider certification, production approval or named site values are asserted |

### Reading paths

Architecture and security reviewers: Parts I–III, sections 34 and 47–49, and Appendices C/E/J. Implementers: Parts II–V and the typed schema package. Operators: sections 27–30 and Parts VI–VII. All roles use the generated requirement/test links rather than a manually curated subset.

### Revision provenance

The original WSD, SDI, ZIP, service-binding, route-authority and stable-fabric thesis is retained. Research-backed corrections and locally proposed extensions are identified by source references and the migration/audit registers. Numerical examples are not presented as government-mandated thresholds. The exact revised text for every original requirement is included in the companion migration catalogue. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)\]

### Navigation

The contents below are a populated Word TOC field. Headings, figure numbers, bookmarks and source links remain editable. After later edits, update fields in Word and save before distributing a new reading copy. Appendix C indexes every normative requirement to its defining chapter, owner, test and source basis.
