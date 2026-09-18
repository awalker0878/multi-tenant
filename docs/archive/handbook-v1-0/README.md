# Original secure-hosting handbook

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

## Chapters

- [Document Control](01-document-control.md)
- [Executive Summary](02-executive-summary.md)
- [Part I — Foundations](03-part-i-foundations.md)
- [1. Purpose, Scope, and Intended Use](1-purpose-scope-and-intended-use.md)
- [2. Normative Language and Architectural Invariants](2-normative-language-and-architectural-invariants.md)
- [3. Security Standards Context](3-security-standards-context.md)
- [4. Core Conceptual Model](4-core-conceptual-model.md)
- [5. Threat and Trust Model](5-threat-and-trust-model.md)
- [Part II — Reference Architecture](09-part-ii-reference-architecture.md)
- [6. High-Level Reference Architecture](6-high-level-reference-architecture.md)
- [7. Tenant Namespace](7-tenant-namespace.md)
- [8. Workload Security Domain](8-workload-security-domain.md)
- [9. Security Domain Instance](9-security-domain-instance.md)
- [10. Security Zone Semantics](10-security-zone-semantics.md)
- [11. ZIP and Security Edge Architecture](11-zip-and-security-edge-architecture.md)
- [12. Management and Out-of-Band Architecture](12-management-and-out-of-band-architecture.md)
- [13. Physical Fabric](13-physical-fabric.md)
- [14. Platform Overlay Architecture](14-platform-overlay-architecture.md)
- [15. Routing Architecture and Route Authority](15-routing-architecture-and-route-authority.md)
- [16. IP Address Management](16-ip-address-management.md)
- [17. IPv6 and Dual-Stack](17-ipv6-and-dual-stack.md)
- [18. Shared Services and Service Bindings](18-shared-services-and-service-bindings.md)
- [19. Public Ingress and Internet Egress](19-public-ingress-and-internet-egress.md)
- [20. Workload Microsegmentation](20-workload-microsegmentation.md)
- [21. Multi-Site and Disaster-Recovery Network Design](21-multi-site-and-disaster-recovery-network-design.md)
- [Part III — Platform Implementation Profiles](26-part-iii-platform-implementation-profiles.md)
- [22. Portability and Platform Conformance](22-portability-and-platform-conformance.md)
- [23. Nutanix Implementation Profile](23-nutanix-implementation-profile.md)
- [24. VMware / NSX Implementation Profile](24-vmware-nsx-implementation-profile.md)
- [25. OpenStack Implementation Profile](25-openstack-implementation-profile.md)
- [26. Bare Metal and Future Platforms](26-bare-metal-and-future-platforms.md)
- [27. Platform Capability Registry](27-platform-capability-registry.md)
- [Part IV — Zero-Touch Automation and Terraform](33-part-iv-zero-touch-automation-and-terraform.md)
- [28. Canonical Hosting API](28-canonical-hosting-api.md)
- [29. Zero-Touch Provisioning Workflow](29-zero-touch-provisioning-workflow.md)
- [30. Terraform Architecture](30-terraform-architecture.md)
- [31. State Boundaries](31-state-boundaries.md)
- [32. Policy as Code and Security Admission](32-policy-as-code-and-security-admission.md)
- [33. Secrets and Automation Credentials](33-secrets-and-automation-credentials.md)
- [34. CI/CD and Change Gates](34-ci-cd-and-change-gates.md)
- [35. Drift and Reconciliation](35-drift-and-reconciliation.md)
- [Part V — Assurance, Testing, and Operations](42-part-v-assurance-testing-and-operations.md)
- [36. Assurance Profiles](36-assurance-profiles.md)
- [37. Conformance Test Framework](37-conformance-test-framework.md)
- [38. Deployment Evidence](38-deployment-evidence.md)
- [39. Logging, Telemetry, and Observability](39-logging-telemetry-and-observability.md)
- [40. Capacity and Performance Engineering](40-capacity-and-performance-engineering.md)
- [41. High Availability and Failure Behaviour](41-high-availability-and-failure-behaviour.md)
- [42. Backup and Restore](42-backup-and-restore.md)
- [43. Incident Response and Containment](43-incident-response-and-containment.md)
- [44. Change and Exception Management](44-change-and-exception-management.md)
- [45. Lifecycle and Offboarding](45-lifecycle-and-offboarding.md)
- [46. Migration and Transition Connectivity](46-migration-and-transition-connectivity.md)
- [Part VI — Governance and Delivery](54-part-vi-governance-and-delivery.md)
- [47. Operating Model and Separation of Duties](47-operating-model-and-separation-of-duties.md)
- [48. Architecture Review Checklist](48-architecture-review-checklist.md)
- [49. Tenant / WSD Onboarding Checklist](49-tenant-wsd-onboarding-checklist.md)
- [50. Delivery Roadmap](50-delivery-roadmap.md)
- [51. Initial Reference Implementation](51-initial-reference-implementation.md)
- [52. Architecture Acceptance Criteria](52-architecture-acceptance-criteria.md)
- [Appendix A — Canonical Object Model](61-appendix-a-canonical-object-model.md)
- [Appendix B — Terraform Root and Module Patterns](62-appendix-b-terraform-root-and-module-patterns.md)
- [Appendix C — Baseline Policy Matrix](63-appendix-c-baseline-policy-matrix.md)
- [Appendix D — Conformance Test Catalogue](64-appendix-d-conformance-test-catalogue.md)
- [Appendix E — Evidence Manifest](65-appendix-e-evidence-manifest.md)
- [Appendix F — Architecture Decision Record Template](66-appendix-f-architecture-decision-record-template.md)
- [Appendix G — Glossary](67-appendix-g-glossary.md)
- [Appendix H — Normative Requirement Catalogue](68-appendix-h-normative-requirement-catalogue.md)
- [Appendix I — References](69-appendix-i-references.md)
- [Closing Architecture Statement](70-closing-architecture-statement.md)

## Source front matter
PORTABLE MULTI-TENANT<br>SECURE HOSTING

Architecture Standard, Engineering Handbook, and Zero-Touch Automation Blueprint

Greenfield Reference Architecture

Government-aligned security zoning • vendor-neutral service contract • platform adapters • secure by default

Draft v1.0  \|  September 2026
