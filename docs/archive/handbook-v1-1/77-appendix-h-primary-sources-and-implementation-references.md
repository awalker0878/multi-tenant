# Appendix H — Primary sources and implementation references

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13449_1645000677"></a>
<a id="app_H"></a>

Research review date: 16 September 2026. References distinguish uploaded baseline, applicable organizational sources, Cyber Centre guidance, protocol specifications and implementation documentation. Vendor repositories and current web pages are discovery/documentation sources, not pinned production qualification records. The implementation register must preserve the exact product/API/provider tuple and source snapshot used for qualification.

<a id="S00"></a>

[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) — Uploaded handbook, Draft v1.0

September 2026  \|  User-provided baseline

Source lineage; 43 pages; all 99 original requirement/invariant IDs retained or explicitly revised. Not an external authority.

Source: uploaded Portable\_Multi-Tenant\_Secure\_Hosting\_Handbook(2).docx; Draft v1.0, 43 pages.

<a id="S01"></a>

[S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) — ITSP.80.022 - Baseline security requirements for network security zones, version 2.0

Effective 2021-01-12  \|  Cyber Centre guidance

Sections 2-4 and annexes A-F. Zone definitions, joint ZIP authority and management boundaries. Architecture requirements in this handbook are local translations, not quotations.

[Open official source: ITSP.80.022 - Baseline security requirements for network security zones, version 2.0](https://www.cyber.gc.ca/en/guidance/baseline-security-requirements-network-security-zones-version-20-itsp80022)

<a id="S02"></a>

[S02](77-appendix-h-primary-sources-and-implementation-references.md#S02) — ITSP.80.023 - Cloud network security zones

Effective 2023-06-12  \|  Cyber Centre guidance

Companion to ITSP.80.022; cloud ZIP functions, isolated MZ approach and control/data-plane distinctions. Limited to Unclassified/Protected A/Protected B context.

[Open official source: ITSP.80.023 - Cloud network security zones](https://www.cyber.gc.ca/en/guidance/cloud-network-security-zones-itsp80023)

<a id="S03"></a>

[S03](77-appendix-h-primary-sources-and-implementation-references.md#S03) — ITSP.70.010 - Best practices for data centre virtualization

Effective 2020-03-27  \|  Cyber Centre guidance

Section 3: strong recommendation against co-locating VMs from different network security zones on the same physical hardware. Sharing requires explicit risk analysis, not a VPC claim.

[Open official source: ITSP.70.010 - Best practices for data centre virtualization](https://www.cyber.gc.ca/en/guidance/cyber-centre-data-centre-virtualization-report-best-practices-data-centre-virtualization)

<a id="S04"></a>

[S04](77-appendix-h-primary-sources-and-implementation-references.md#S04) — ITSG-33 - IT security risk management: A lifecycle approach

2012; legacy catalogue transition noted  \|  Cyber Centre lifecycle reference

Retained for original ISSIP/lifecycle lineage. Do not treat Annex 3A as the current control catalogue.

[Open official source: ITSG-33 - IT security risk management: A lifecycle approach](https://www.cyber.gc.ca/en/guidance/it-security-risk-management-lifecycle-approach-itsg-33)

<a id="S05"></a>

[S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) — ITSP.10.033 - Security and privacy controls and assurance activities catalogue: Foreword, overview, introduction

Effective 2026-03-31  \|  Cyber Centre control catalogue

Explicitly supersedes ITSG-33 Annex 3A. Canadian-specific 100-series identifiers move to 400-series. Source families are starting points for tailoring, not automatic control equivalence.

[Open official source: ITSP.10.033 - Security and privacy controls and assurance activities catalogue: Foreword, overview, introduction](https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction)

<a id="S06"></a>

[S06](77-appendix-h-primary-sources-and-implementation-references.md#S06) — Government of Canada Security Control Profile for Cloud-based GC Services

Public page reviewed 2026-09-16  \|  GC profile; applicability decision required

PBMM context retained from baseline; register the exact adopted profile/version and reconcile legacy control references with the applicable catalogue.

[Open official source: Government of Canada Security Control Profile for Cloud-based GC Services](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/cloud-services/government-canada-security-control-profile-cloud-based-it-services.html)

<a id="S07"></a>

[S07](77-appendix-h-primary-sources-and-implementation-references.md#S07) — System Management Configuration Requirements

Public page reviewed 2026-09-16  \|  GC configuration requirements; verify organizational applicability

Sections 1-4 cover supported lifecycle, hardening, vulnerability management and secure administration including phishing-resistant MFA.

[Open official source: System Management Configuration Requirements](https://www.canada.ca/en/government/system/digital-government/policies-standards/enterprise-it-service-common-configurations/system.html)

<a id="S08"></a>

[S08](77-appendix-h-primary-sources-and-implementation-references.md#S08) — ITSP.50.104 - Guidance on defence in depth for cloud-based services

2020  \|  Cyber Centre guidance

Used as a completeness lens spanning governance, compute/network, data, IAM, applications and operations.

[Open official source: ITSP.50.104 - Guidance on defence in depth for cloud-based services](https://www.cyber.gc.ca/en/guidance/itsp50104-guidance-defence-depth-cloud-based-services)

<a id="S09"></a>

[S09](77-appendix-h-primary-sources-and-implementation-references.md#S09) — ITSP.50.106 - Guidance on cloud service cryptography

2020  \|  Cyber Centre guidance

Key ownership, lifecycle and cloud cryptographic responsibility context; not a product approval.

[Open official source: ITSP.50.106 - Guidance on cloud service cryptography](https://www.cyber.gc.ca/en/guidance/guidance-cloud-service-cryptography-itsp50106)

<a id="S10"></a>

[S10](77-appendix-h-primary-sources-and-implementation-references.md#S10) — ITSP.40.111 - Cryptographic algorithms for Unclassified, Protected A and Protected B information, version 5

Effective 2026-05-29  \|  Cyber Centre cryptographic guidance

Use a versioned cryptographic profile and migration inventory; a fixed legacy algorithm list is insufficient.

[Open official source: ITSP.40.111 - Cryptographic algorithms for Unclassified, Protected A and Protected B information, version 5](https://www.cyber.gc.ca/en/guidance/cryptographic-algorithms-unclassified-protected-protected-b-information-itsp40111)

<a id="S11"></a>

[S11](77-appendix-h-primary-sources-and-implementation-references.md#S11) — Event Logging Guidance

Public page reviewed 2026-09-16  \|  GC operational guidance

Centralized protected event collection, event classes and operational ownership. Local retention examples are not attributed as GC-mandated durations.

[Open official source: Event Logging Guidance](https://www.canada.ca/en/government/system/digital-government/online-security-privacy/cyber-security-guidance-policy/event-logging-guidance.html)

<a id="S12"></a>

[S12](77-appendix-h-primary-sources-and-implementation-references.md#S12) — Government of Canada Cyber Security Event Management Plan

Public page reviewed 2026-09-16  \|  GC event-management framework

Coordinate local runbooks with applicable preparation, detection/assessment, mitigation/recovery and post-event processes.

[Open official source: Government of Canada Cyber Security Event Management Plan](https://www.canada.ca/en/government/system/digital-government/online-security-privacy/cyber-security-guidance-policy/management-security-incidents/government-canada-cyber-security-event-management-plan.html)

<a id="S13"></a>

[S13](77-appendix-h-primary-sources-and-implementation-references.md#S13) — Terraform - Providers within modules

Documentation snapshot 2026-09-16  \|  Implementation documentation

Provider configuration in root modules; explicit provider passing and aliases where required.

[Open official source: Terraform - Providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers)

<a id="S14"></a>

[S14](77-appendix-h-primary-sources-and-implementation-references.md#S14) — Terraform - Dependency lock file

Documentation snapshot 2026-09-16  \|  Implementation documentation

Locks provider selections/checksums, not remote module selections; pin module versions or immutable revisions separately.

[Open official source: Terraform - Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)

<a id="S15"></a>

[S15](77-appendix-h-primary-sources-and-implementation-references.md#S15) — Terraform - Ephemeral values

Documentation snapshot 2026-09-16  \|  Implementation documentation

Supported ephemeral values can be omitted from persisted plan/state; availability depends on Terraform and provider/resource support.

[Open official source: Terraform - Ephemeral values](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/ephemeral)

<a id="S16"></a>

[S16](77-appendix-h-primary-sources-and-implementation-references.md#S16) — Terraform - Write-only arguments

Documentation snapshot 2026-09-16  \|  Implementation documentation

Resource-specific write-only arguments; not a blanket guarantee that a provider never persists secrets.

[Open official source: Terraform - Write-only arguments](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/write-only)

<a id="S17"></a>

[S17](77-appendix-h-primary-sources-and-implementation-references.md#S17) — Nutanix Terraform provider - official repository

README identifies v2.4.2 at review  \|  Implementation documentation, not certification

Reviewed resource mappings and compatibility notes. Example version 2.4.2 is a documentation reference, not an approved production stack.

[Open official source: Nutanix Terraform provider - official repository](https://github.com/nutanix/terraform-provider-nutanix)

<a id="S18"></a>

[S18](77-appendix-h-primary-sources-and-implementation-references.md#S18) — VMware NSX Terraform provider - official repository

Documentation snapshot 2026-09-16  \|  Implementation documentation, not certification

Provider provenance and NSX realization context; exact product/provider tuple must be qualified before placement.

[Open official source: VMware NSX Terraform provider - official repository](https://github.com/vmware/terraform-provider-nsxt)

<a id="S19"></a>

[S19](77-appendix-h-primary-sources-and-implementation-references.md#S19) — OpenStack Terraform provider - official repository

Documentation snapshot 2026-09-16  \|  Implementation documentation, not certification

Provider provenance. Distribution, Neutron backend and enabled extensions must be recorded independently.

[Open official source: OpenStack Terraform provider - official repository](https://github.com/terraform-provider-openstack/terraform-provider-openstack)

<a id="S20"></a>

[S20](77-appendix-h-primary-sources-and-implementation-references.md#S20) — RFC 8212 - Default External BGP route propagation behavior without policies

2017  \|  IETF technical specification

Import/export policy requirements inform the provider-owned fabric profile; confirm vendor implementation behavior.

[Open official source: RFC 8212 - Default External BGP route propagation behavior without policies](https://www.rfc-editor.org/info/rfc8212/)

<a id="S21"></a>

[S21](77-appendix-h-primary-sources-and-implementation-references.md#S21) — RFC 7432 - BGP MPLS-Based Ethernet VPN

2015; update/errata chain reviewed  \|  IETF technical specification

Foundational EVPN signaling and multihoming concepts; it is not by itself a VXLAN conformance claim.

[Open official source: RFC 7432 - BGP MPLS-Based Ethernet VPN](https://datatracker.ietf.org/doc/html/rfc7432)

<a id="S22"></a>

[S22](77-appendix-h-primary-sources-and-implementation-references.md#S22) — RFC 8365 - A network virtualization overlay solution using EVPN

2018  \|  IETF technical specification

EVPN overlay use. Qualify extensions and interoperability rather than assuming equal product feature sets.

[Open official source: RFC 8365 - A network virtualization overlay solution using EVPN](https://datatracker.ietf.org/doc/html/rfc8365)

<a id="S23"></a>

[S23](77-appendix-h-primary-sources-and-implementation-references.md#S23) — RFC 8200 - Internet Protocol, Version 6 specification

2017  \|  IETF technical specification

IPv6 transport foundation; security semantics and operational profiles remain explicit.

[Open official source: RFC 8200 - Internet Protocol, Version 6 specification](https://datatracker.ietf.org/doc/html/rfc8200)

<a id="S24"></a>

[S24](77-appendix-h-primary-sources-and-implementation-references.md#S24) — RFC 4890 - Recommendations for filtering ICMPv6 messages in firewalls

2007  \|  IETF guidance

Avoid blanket ICMPv6 denial that breaks required protocol operation; filter by the selected profile.

[Open official source: RFC 4890 - Recommendations for filtering ICMPv6 messages in firewalls](https://datatracker.ietf.org/doc/html/rfc4890)

<a id="S25"></a>

[S25](77-appendix-h-primary-sources-and-implementation-references.md#S25) — Kubernetes - Multi-tenancy

Documentation snapshot 2026-09-16  \|  Implementation documentation

Namespace isolation is not a complete hostile-tenant boundary; compute/control-plane choices require threat analysis.

[Open official source: Kubernetes - Multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)

<a id="S26"></a>

[S26](77-appendix-h-primary-sources-and-implementation-references.md#S26) — Kubernetes - Network Policies

Documentation snapshot 2026-09-16  \|  Implementation documentation

NetworkPolicy depends on enforcement support; connectivity policy does not replace identity, host or storage controls.

[Open official source: Kubernetes - Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

<a id="S27"></a>

[S27](77-appendix-h-primary-sources-and-implementation-references.md#S27) — NIST SP 800-88 Revision 2 - Guidelines for Media Sanitization

Final 2025  \|  Supporting technical guidance; GC tailoring required

Sanitization methods and verification; use applicable GC media-handling rules and approved technical methods.

[Open official source: NIST SP 800-88 Revision 2 - Guidelines for Media Sanitization](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

<a id="S28"></a>

[S28](77-appendix-h-primary-sources-and-implementation-references.md#S28) — Government of Canada Enterprise Architecture Framework

Public page reviewed 2026-09-16  \|  GC architecture guidance; verify applicability

Architecture governance and reuse context. Product neutrality and exit tests below are explicit handbook design decisions.

[Open official source: Government of Canada Enterprise Architecture Framework](https://www.canada.ca/en/government/system/digital-government/policies-standards/government-canada-enterprise-architecture-framework.html)

<a id="S29"></a>

[S29](77-appendix-h-primary-sources-and-implementation-references.md#S29) — ITSG-38 - Network security zoning: Design considerations for placement of services within zones

Public page reviewed 2026-09-16  \|  Cyber Centre guidance

Supporting service-placement context; source-version reconciliation belongs to the security authority.

[Open official source: ITSG-38 - Network security zoning: Design considerations for placement of services within zones](https://www.cyber.gc.ca/en/guidance/network-security-zoning-design-considerations-placement-services-within-zones-itsg-38)

<a id="S30"></a>

[S30](77-appendix-h-primary-sources-and-implementation-references.md#S30) — JSON Schema Draft 2020-12

2020-12 specification  \|  Contract specification

Machine-readable companion schemas use this dialect. Semantic admission and authorization are separate checks.

[Open official source: JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)

[Previous chapter](76-appendix-g-operational-records-and-decision-templates.md) · [Chapter index](README.md) · [Next chapter](78-appendix-i-glossary.md)
