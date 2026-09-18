# Appendix H — Primary sources and implementation references

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:1557 BEGIN -->

<a id="__RefHeading___Toc13449_1645000677"></a>
<a id="app_H"></a>

<!-- SOURCE-BLOCK HB11:1557 END -->

<!-- SOURCE-BLOCK HB11:1558 BEGIN -->

Research review date: 16 September 2026. References distinguish uploaded baseline, applicable organizational sources, Cyber Centre guidance, protocol specifications and implementation documentation. Vendor repositories and current web pages are discovery/documentation sources, not pinned production qualification records. The implementation register must preserve the exact product/API/provider tuple and source snapshot used for qualification.

<!-- SOURCE-BLOCK HB11:1558 END -->

<!-- SOURCE-BLOCK HB11:1559 BEGIN -->

<a id="S00"></a>

[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) — Uploaded handbook, Draft v1.0

<!-- SOURCE-BLOCK HB11:1559 END -->

<!-- SOURCE-BLOCK HB11:1560 BEGIN -->

September 2026  \|  User-provided baseline

<!-- SOURCE-BLOCK HB11:1560 END -->

<!-- SOURCE-BLOCK HB11:1561 BEGIN -->

Source lineage; 43 pages; all 99 original requirement/invariant IDs retained or explicitly revised. Not an external authority.

<!-- SOURCE-BLOCK HB11:1561 END -->

<!-- SOURCE-BLOCK HB11:1562 BEGIN -->

Source: uploaded Portable\_Multi-Tenant\_Secure\_Hosting\_Handbook(2).docx; Draft v1.0, 43 pages.

<!-- SOURCE-BLOCK HB11:1562 END -->

<!-- SOURCE-BLOCK HB11:1563 BEGIN -->

<a id="S01"></a>

[S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) — ITSP.80.022 - Baseline security requirements for network security zones, version 2.0

<!-- SOURCE-BLOCK HB11:1563 END -->

<!-- SOURCE-BLOCK HB11:1564 BEGIN -->

Effective 2021-01-12  \|  Cyber Centre guidance

<!-- SOURCE-BLOCK HB11:1564 END -->

<!-- SOURCE-BLOCK HB11:1565 BEGIN -->

Sections 2-4 and annexes A-F. Zone definitions, joint ZIP authority and management boundaries. Architecture requirements in this handbook are local translations, not quotations.

<!-- SOURCE-BLOCK HB11:1565 END -->

<!-- SOURCE-BLOCK HB11:1566 BEGIN -->

[Open official source: ITSP.80.022 - Baseline security requirements for network security zones, version 2.0](https://www.cyber.gc.ca/en/guidance/baseline-security-requirements-network-security-zones-version-20-itsp80022)

<!-- SOURCE-BLOCK HB11:1566 END -->

<!-- SOURCE-BLOCK HB11:1567 BEGIN -->

<a id="S02"></a>

[S02](77-appendix-h-primary-sources-and-implementation-references.md#S02) — ITSP.80.023 - Cloud network security zones

<!-- SOURCE-BLOCK HB11:1567 END -->

<!-- SOURCE-BLOCK HB11:1568 BEGIN -->

Effective 2023-06-12  \|  Cyber Centre guidance

<!-- SOURCE-BLOCK HB11:1568 END -->

<!-- SOURCE-BLOCK HB11:1569 BEGIN -->

Companion to ITSP.80.022; cloud ZIP functions, isolated MZ approach and control/data-plane distinctions. Limited to Unclassified/Protected A/Protected B context.

<!-- SOURCE-BLOCK HB11:1569 END -->

<!-- SOURCE-BLOCK HB11:1570 BEGIN -->

[Open official source: ITSP.80.023 - Cloud network security zones](https://www.cyber.gc.ca/en/guidance/cloud-network-security-zones-itsp80023)

<!-- SOURCE-BLOCK HB11:1570 END -->

<!-- SOURCE-BLOCK HB11:1571 BEGIN -->

<a id="S03"></a>

[S03](77-appendix-h-primary-sources-and-implementation-references.md#S03) — ITSP.70.010 - Best practices for data centre virtualization

<!-- SOURCE-BLOCK HB11:1571 END -->

<!-- SOURCE-BLOCK HB11:1572 BEGIN -->

Effective 2020-03-27  \|  Cyber Centre guidance

<!-- SOURCE-BLOCK HB11:1572 END -->

<!-- SOURCE-BLOCK HB11:1573 BEGIN -->

Section 3: strong recommendation against co-locating VMs from different network security zones on the same physical hardware. Sharing requires explicit risk analysis, not a VPC claim.

<!-- SOURCE-BLOCK HB11:1573 END -->

<!-- SOURCE-BLOCK HB11:1574 BEGIN -->

[Open official source: ITSP.70.010 - Best practices for data centre virtualization](https://www.cyber.gc.ca/en/guidance/cyber-centre-data-centre-virtualization-report-best-practices-data-centre-virtualization)

<!-- SOURCE-BLOCK HB11:1574 END -->

<!-- SOURCE-BLOCK HB11:1575 BEGIN -->

<a id="S04"></a>

[S04](77-appendix-h-primary-sources-and-implementation-references.md#S04) — ITSG-33 - IT security risk management: A lifecycle approach

<!-- SOURCE-BLOCK HB11:1575 END -->

<!-- SOURCE-BLOCK HB11:1576 BEGIN -->

2012; legacy catalogue transition noted  \|  Cyber Centre lifecycle reference

<!-- SOURCE-BLOCK HB11:1576 END -->

<!-- SOURCE-BLOCK HB11:1577 BEGIN -->

Retained for original ISSIP/lifecycle lineage. Do not treat Annex 3A as the current control catalogue.

<!-- SOURCE-BLOCK HB11:1577 END -->

<!-- SOURCE-BLOCK HB11:1578 BEGIN -->

[Open official source: ITSG-33 - IT security risk management: A lifecycle approach](https://www.cyber.gc.ca/en/guidance/it-security-risk-management-lifecycle-approach-itsg-33)

<!-- SOURCE-BLOCK HB11:1578 END -->

<!-- SOURCE-BLOCK HB11:1579 BEGIN -->

<a id="S05"></a>

[S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) — ITSP.10.033 - Security and privacy controls and assurance activities catalogue: Foreword, overview, introduction

<!-- SOURCE-BLOCK HB11:1579 END -->

<!-- SOURCE-BLOCK HB11:1580 BEGIN -->

Effective 2026-03-31  \|  Cyber Centre control catalogue

<!-- SOURCE-BLOCK HB11:1580 END -->

<!-- SOURCE-BLOCK HB11:1581 BEGIN -->

Explicitly supersedes ITSG-33 Annex 3A. Canadian-specific 100-series identifiers move to 400-series. Source families are starting points for tailoring, not automatic control equivalence.

<!-- SOURCE-BLOCK HB11:1581 END -->

<!-- SOURCE-BLOCK HB11:1582 BEGIN -->

[Open official source: ITSP.10.033 - Security and privacy controls and assurance activities catalogue: Foreword, overview, introduction](https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction)

<!-- SOURCE-BLOCK HB11:1582 END -->

<!-- SOURCE-BLOCK HB11:1583 BEGIN -->

<a id="S06"></a>

[S06](77-appendix-h-primary-sources-and-implementation-references.md#S06) — Government of Canada Security Control Profile for Cloud-based GC Services

<!-- SOURCE-BLOCK HB11:1583 END -->

<!-- SOURCE-BLOCK HB11:1584 BEGIN -->

Public page reviewed 2026-09-16  \|  GC profile; applicability decision required

<!-- SOURCE-BLOCK HB11:1584 END -->

<!-- SOURCE-BLOCK HB11:1585 BEGIN -->

PBMM context retained from baseline; register the exact adopted profile/version and reconcile legacy control references with the applicable catalogue.

<!-- SOURCE-BLOCK HB11:1585 END -->

<!-- SOURCE-BLOCK HB11:1586 BEGIN -->

[Open official source: Government of Canada Security Control Profile for Cloud-based GC Services](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/cloud-services/government-canada-security-control-profile-cloud-based-it-services.html)

<!-- SOURCE-BLOCK HB11:1586 END -->

<!-- SOURCE-BLOCK HB11:1587 BEGIN -->

<a id="S07"></a>

[S07](77-appendix-h-primary-sources-and-implementation-references.md#S07) — System Management Configuration Requirements

<!-- SOURCE-BLOCK HB11:1587 END -->

<!-- SOURCE-BLOCK HB11:1588 BEGIN -->

Public page reviewed 2026-09-16  \|  GC configuration requirements; verify organizational applicability

<!-- SOURCE-BLOCK HB11:1588 END -->

<!-- SOURCE-BLOCK HB11:1589 BEGIN -->

Sections 1-4 cover supported lifecycle, hardening, vulnerability management and secure administration including phishing-resistant MFA.

<!-- SOURCE-BLOCK HB11:1589 END -->

<!-- SOURCE-BLOCK HB11:1590 BEGIN -->

[Open official source: System Management Configuration Requirements](https://www.canada.ca/en/government/system/digital-government/policies-standards/enterprise-it-service-common-configurations/system.html)

<!-- SOURCE-BLOCK HB11:1590 END -->

<!-- SOURCE-BLOCK HB11:1591 BEGIN -->

<a id="S08"></a>

[S08](77-appendix-h-primary-sources-and-implementation-references.md#S08) — ITSP.50.104 - Guidance on defence in depth for cloud-based services

<!-- SOURCE-BLOCK HB11:1591 END -->

<!-- SOURCE-BLOCK HB11:1592 BEGIN -->

2020  \|  Cyber Centre guidance

<!-- SOURCE-BLOCK HB11:1592 END -->

<!-- SOURCE-BLOCK HB11:1593 BEGIN -->

Used as a completeness lens spanning governance, compute/network, data, IAM, applications and operations.

<!-- SOURCE-BLOCK HB11:1593 END -->

<!-- SOURCE-BLOCK HB11:1594 BEGIN -->

[Open official source: ITSP.50.104 - Guidance on defence in depth for cloud-based services](https://www.cyber.gc.ca/en/guidance/itsp50104-guidance-defence-depth-cloud-based-services)

<!-- SOURCE-BLOCK HB11:1594 END -->

<!-- SOURCE-BLOCK HB11:1595 BEGIN -->

<a id="S09"></a>

[S09](77-appendix-h-primary-sources-and-implementation-references.md#S09) — ITSP.50.106 - Guidance on cloud service cryptography

<!-- SOURCE-BLOCK HB11:1595 END -->

<!-- SOURCE-BLOCK HB11:1596 BEGIN -->

2020  \|  Cyber Centre guidance

<!-- SOURCE-BLOCK HB11:1596 END -->

<!-- SOURCE-BLOCK HB11:1597 BEGIN -->

Key ownership, lifecycle and cloud cryptographic responsibility context; not a product approval.

<!-- SOURCE-BLOCK HB11:1597 END -->

<!-- SOURCE-BLOCK HB11:1598 BEGIN -->

[Open official source: ITSP.50.106 - Guidance on cloud service cryptography](https://www.cyber.gc.ca/en/guidance/guidance-cloud-service-cryptography-itsp50106)

<!-- SOURCE-BLOCK HB11:1598 END -->

<!-- SOURCE-BLOCK HB11:1599 BEGIN -->

<a id="S10"></a>

[S10](77-appendix-h-primary-sources-and-implementation-references.md#S10) — ITSP.40.111 - Cryptographic algorithms for Unclassified, Protected A and Protected B information, version 5

<!-- SOURCE-BLOCK HB11:1599 END -->

<!-- SOURCE-BLOCK HB11:1600 BEGIN -->

Effective 2026-05-29  \|  Cyber Centre cryptographic guidance

<!-- SOURCE-BLOCK HB11:1600 END -->

<!-- SOURCE-BLOCK HB11:1601 BEGIN -->

Use a versioned cryptographic profile and migration inventory; a fixed legacy algorithm list is insufficient.

<!-- SOURCE-BLOCK HB11:1601 END -->

<!-- SOURCE-BLOCK HB11:1602 BEGIN -->

[Open official source: ITSP.40.111 - Cryptographic algorithms for Unclassified, Protected A and Protected B information, version 5](https://www.cyber.gc.ca/en/guidance/cryptographic-algorithms-unclassified-protected-protected-b-information-itsp40111)

<!-- SOURCE-BLOCK HB11:1602 END -->

<!-- SOURCE-BLOCK HB11:1603 BEGIN -->

<a id="S11"></a>

[S11](77-appendix-h-primary-sources-and-implementation-references.md#S11) — Event Logging Guidance

<!-- SOURCE-BLOCK HB11:1603 END -->

<!-- SOURCE-BLOCK HB11:1604 BEGIN -->

Public page reviewed 2026-09-16  \|  GC operational guidance

<!-- SOURCE-BLOCK HB11:1604 END -->

<!-- SOURCE-BLOCK HB11:1605 BEGIN -->

Centralized protected event collection, event classes and operational ownership. Local retention examples are not attributed as GC-mandated durations.

<!-- SOURCE-BLOCK HB11:1605 END -->

<!-- SOURCE-BLOCK HB11:1606 BEGIN -->

[Open official source: Event Logging Guidance](https://www.canada.ca/en/government/system/digital-government/online-security-privacy/cyber-security-guidance-policy/event-logging-guidance.html)

<!-- SOURCE-BLOCK HB11:1606 END -->

<!-- SOURCE-BLOCK HB11:1607 BEGIN -->

<a id="S12"></a>

[S12](77-appendix-h-primary-sources-and-implementation-references.md#S12) — Government of Canada Cyber Security Event Management Plan

<!-- SOURCE-BLOCK HB11:1607 END -->

<!-- SOURCE-BLOCK HB11:1608 BEGIN -->

Public page reviewed 2026-09-16  \|  GC event-management framework

<!-- SOURCE-BLOCK HB11:1608 END -->

<!-- SOURCE-BLOCK HB11:1609 BEGIN -->

Coordinate local runbooks with applicable preparation, detection/assessment, mitigation/recovery and post-event processes.

<!-- SOURCE-BLOCK HB11:1609 END -->

<!-- SOURCE-BLOCK HB11:1610 BEGIN -->

[Open official source: Government of Canada Cyber Security Event Management Plan](https://www.canada.ca/en/government/system/digital-government/online-security-privacy/cyber-security-guidance-policy/management-security-incidents/government-canada-cyber-security-event-management-plan.html)

<!-- SOURCE-BLOCK HB11:1610 END -->

<!-- SOURCE-BLOCK HB11:1611 BEGIN -->

<a id="S13"></a>

[S13](77-appendix-h-primary-sources-and-implementation-references.md#S13) — Terraform - Providers within modules

<!-- SOURCE-BLOCK HB11:1611 END -->

<!-- SOURCE-BLOCK HB11:1612 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation

<!-- SOURCE-BLOCK HB11:1612 END -->

<!-- SOURCE-BLOCK HB11:1613 BEGIN -->

Provider configuration in root modules; explicit provider passing and aliases where required.

<!-- SOURCE-BLOCK HB11:1613 END -->

<!-- SOURCE-BLOCK HB11:1614 BEGIN -->

[Open official source: Terraform - Providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers)

<!-- SOURCE-BLOCK HB11:1614 END -->

<!-- SOURCE-BLOCK HB11:1615 BEGIN -->

<a id="S14"></a>

[S14](77-appendix-h-primary-sources-and-implementation-references.md#S14) — Terraform - Dependency lock file

<!-- SOURCE-BLOCK HB11:1615 END -->

<!-- SOURCE-BLOCK HB11:1616 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation

<!-- SOURCE-BLOCK HB11:1616 END -->

<!-- SOURCE-BLOCK HB11:1617 BEGIN -->

Locks provider selections/checksums, not remote module selections; pin module versions or immutable revisions separately.

<!-- SOURCE-BLOCK HB11:1617 END -->

<!-- SOURCE-BLOCK HB11:1618 BEGIN -->

[Open official source: Terraform - Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)

<!-- SOURCE-BLOCK HB11:1618 END -->

<!-- SOURCE-BLOCK HB11:1619 BEGIN -->

<a id="S15"></a>

[S15](77-appendix-h-primary-sources-and-implementation-references.md#S15) — Terraform - Ephemeral values

<!-- SOURCE-BLOCK HB11:1619 END -->

<!-- SOURCE-BLOCK HB11:1620 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation

<!-- SOURCE-BLOCK HB11:1620 END -->

<!-- SOURCE-BLOCK HB11:1621 BEGIN -->

Supported ephemeral values can be omitted from persisted plan/state; availability depends on Terraform and provider/resource support.

<!-- SOURCE-BLOCK HB11:1621 END -->

<!-- SOURCE-BLOCK HB11:1622 BEGIN -->

[Open official source: Terraform - Ephemeral values](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/ephemeral)

<!-- SOURCE-BLOCK HB11:1622 END -->

<!-- SOURCE-BLOCK HB11:1623 BEGIN -->

<a id="S16"></a>

[S16](77-appendix-h-primary-sources-and-implementation-references.md#S16) — Terraform - Write-only arguments

<!-- SOURCE-BLOCK HB11:1623 END -->

<!-- SOURCE-BLOCK HB11:1624 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation

<!-- SOURCE-BLOCK HB11:1624 END -->

<!-- SOURCE-BLOCK HB11:1625 BEGIN -->

Resource-specific write-only arguments; not a blanket guarantee that a provider never persists secrets.

<!-- SOURCE-BLOCK HB11:1625 END -->

<!-- SOURCE-BLOCK HB11:1626 BEGIN -->

[Open official source: Terraform - Write-only arguments](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/write-only)

<!-- SOURCE-BLOCK HB11:1626 END -->

<!-- SOURCE-BLOCK HB11:1627 BEGIN -->

<a id="S17"></a>

[S17](77-appendix-h-primary-sources-and-implementation-references.md#S17) — Nutanix Terraform provider - official repository

<!-- SOURCE-BLOCK HB11:1627 END -->

<!-- SOURCE-BLOCK HB11:1628 BEGIN -->

README identifies v2.4.2 at review  \|  Implementation documentation, not certification

<!-- SOURCE-BLOCK HB11:1628 END -->

<!-- SOURCE-BLOCK HB11:1629 BEGIN -->

Reviewed resource mappings and compatibility notes. Example version 2.4.2 is a documentation reference, not an approved production stack.

<!-- SOURCE-BLOCK HB11:1629 END -->

<!-- SOURCE-BLOCK HB11:1630 BEGIN -->

[Open official source: Nutanix Terraform provider - official repository](https://github.com/nutanix/terraform-provider-nutanix)

<!-- SOURCE-BLOCK HB11:1630 END -->

<!-- SOURCE-BLOCK HB11:1631 BEGIN -->

<a id="S18"></a>

[S18](77-appendix-h-primary-sources-and-implementation-references.md#S18) — VMware NSX Terraform provider - official repository

<!-- SOURCE-BLOCK HB11:1631 END -->

<!-- SOURCE-BLOCK HB11:1632 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation, not certification

<!-- SOURCE-BLOCK HB11:1632 END -->

<!-- SOURCE-BLOCK HB11:1633 BEGIN -->

Provider provenance and NSX realization context; exact product/provider tuple must be qualified before placement.

<!-- SOURCE-BLOCK HB11:1633 END -->

<!-- SOURCE-BLOCK HB11:1634 BEGIN -->

[Open official source: VMware NSX Terraform provider - official repository](https://github.com/vmware/terraform-provider-nsxt)

<!-- SOURCE-BLOCK HB11:1634 END -->

<!-- SOURCE-BLOCK HB11:1635 BEGIN -->

<a id="S19"></a>

[S19](77-appendix-h-primary-sources-and-implementation-references.md#S19) — OpenStack Terraform provider - official repository

<!-- SOURCE-BLOCK HB11:1635 END -->

<!-- SOURCE-BLOCK HB11:1636 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation, not certification

<!-- SOURCE-BLOCK HB11:1636 END -->

<!-- SOURCE-BLOCK HB11:1637 BEGIN -->

Provider provenance. Distribution, Neutron backend and enabled extensions must be recorded independently.

<!-- SOURCE-BLOCK HB11:1637 END -->

<!-- SOURCE-BLOCK HB11:1638 BEGIN -->

[Open official source: OpenStack Terraform provider - official repository](https://github.com/terraform-provider-openstack/terraform-provider-openstack)

<!-- SOURCE-BLOCK HB11:1638 END -->

<!-- SOURCE-BLOCK HB11:1639 BEGIN -->

<a id="S20"></a>

[S20](77-appendix-h-primary-sources-and-implementation-references.md#S20) — RFC 8212 - Default External BGP route propagation behavior without policies

<!-- SOURCE-BLOCK HB11:1639 END -->

<!-- SOURCE-BLOCK HB11:1640 BEGIN -->

2017  \|  IETF technical specification

<!-- SOURCE-BLOCK HB11:1640 END -->

<!-- SOURCE-BLOCK HB11:1641 BEGIN -->

Import/export policy requirements inform the provider-owned fabric profile; confirm vendor implementation behavior.

<!-- SOURCE-BLOCK HB11:1641 END -->

<!-- SOURCE-BLOCK HB11:1642 BEGIN -->

[Open official source: RFC 8212 - Default External BGP route propagation behavior without policies](https://www.rfc-editor.org/info/rfc8212/)

<!-- SOURCE-BLOCK HB11:1642 END -->

<!-- SOURCE-BLOCK HB11:1643 BEGIN -->

<a id="S21"></a>

[S21](77-appendix-h-primary-sources-and-implementation-references.md#S21) — RFC 7432 - BGP MPLS-Based Ethernet VPN

<!-- SOURCE-BLOCK HB11:1643 END -->

<!-- SOURCE-BLOCK HB11:1644 BEGIN -->

2015; update/errata chain reviewed  \|  IETF technical specification

<!-- SOURCE-BLOCK HB11:1644 END -->

<!-- SOURCE-BLOCK HB11:1645 BEGIN -->

Foundational EVPN signaling and multihoming concepts; it is not by itself a VXLAN conformance claim.

<!-- SOURCE-BLOCK HB11:1645 END -->

<!-- SOURCE-BLOCK HB11:1646 BEGIN -->

[Open official source: RFC 7432 - BGP MPLS-Based Ethernet VPN](https://datatracker.ietf.org/doc/html/rfc7432)

<!-- SOURCE-BLOCK HB11:1646 END -->

<!-- SOURCE-BLOCK HB11:1647 BEGIN -->

<a id="S22"></a>

[S22](77-appendix-h-primary-sources-and-implementation-references.md#S22) — RFC 8365 - A network virtualization overlay solution using EVPN

<!-- SOURCE-BLOCK HB11:1647 END -->

<!-- SOURCE-BLOCK HB11:1648 BEGIN -->

2018  \|  IETF technical specification

<!-- SOURCE-BLOCK HB11:1648 END -->

<!-- SOURCE-BLOCK HB11:1649 BEGIN -->

EVPN overlay use. Qualify extensions and interoperability rather than assuming equal product feature sets.

<!-- SOURCE-BLOCK HB11:1649 END -->

<!-- SOURCE-BLOCK HB11:1650 BEGIN -->

[Open official source: RFC 8365 - A network virtualization overlay solution using EVPN](https://datatracker.ietf.org/doc/html/rfc8365)

<!-- SOURCE-BLOCK HB11:1650 END -->

<!-- SOURCE-BLOCK HB11:1651 BEGIN -->

<a id="S23"></a>

[S23](77-appendix-h-primary-sources-and-implementation-references.md#S23) — RFC 8200 - Internet Protocol, Version 6 specification

<!-- SOURCE-BLOCK HB11:1651 END -->

<!-- SOURCE-BLOCK HB11:1652 BEGIN -->

2017  \|  IETF technical specification

<!-- SOURCE-BLOCK HB11:1652 END -->

<!-- SOURCE-BLOCK HB11:1653 BEGIN -->

IPv6 transport foundation; security semantics and operational profiles remain explicit.

<!-- SOURCE-BLOCK HB11:1653 END -->

<!-- SOURCE-BLOCK HB11:1654 BEGIN -->

[Open official source: RFC 8200 - Internet Protocol, Version 6 specification](https://datatracker.ietf.org/doc/html/rfc8200)

<!-- SOURCE-BLOCK HB11:1654 END -->

<!-- SOURCE-BLOCK HB11:1655 BEGIN -->

<a id="S24"></a>

[S24](77-appendix-h-primary-sources-and-implementation-references.md#S24) — RFC 4890 - Recommendations for filtering ICMPv6 messages in firewalls

<!-- SOURCE-BLOCK HB11:1655 END -->

<!-- SOURCE-BLOCK HB11:1656 BEGIN -->

2007  \|  IETF guidance

<!-- SOURCE-BLOCK HB11:1656 END -->

<!-- SOURCE-BLOCK HB11:1657 BEGIN -->

Avoid blanket ICMPv6 denial that breaks required protocol operation; filter by the selected profile.

<!-- SOURCE-BLOCK HB11:1657 END -->

<!-- SOURCE-BLOCK HB11:1658 BEGIN -->

[Open official source: RFC 4890 - Recommendations for filtering ICMPv6 messages in firewalls](https://datatracker.ietf.org/doc/html/rfc4890)

<!-- SOURCE-BLOCK HB11:1658 END -->

<!-- SOURCE-BLOCK HB11:1659 BEGIN -->

<a id="S25"></a>

[S25](77-appendix-h-primary-sources-and-implementation-references.md#S25) — Kubernetes - Multi-tenancy

<!-- SOURCE-BLOCK HB11:1659 END -->

<!-- SOURCE-BLOCK HB11:1660 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation

<!-- SOURCE-BLOCK HB11:1660 END -->

<!-- SOURCE-BLOCK HB11:1661 BEGIN -->

Namespace isolation is not a complete hostile-tenant boundary; compute/control-plane choices require threat analysis.

<!-- SOURCE-BLOCK HB11:1661 END -->

<!-- SOURCE-BLOCK HB11:1662 BEGIN -->

[Open official source: Kubernetes - Multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)

<!-- SOURCE-BLOCK HB11:1662 END -->

<!-- SOURCE-BLOCK HB11:1663 BEGIN -->

<a id="S26"></a>

[S26](77-appendix-h-primary-sources-and-implementation-references.md#S26) — Kubernetes - Network Policies

<!-- SOURCE-BLOCK HB11:1663 END -->

<!-- SOURCE-BLOCK HB11:1664 BEGIN -->

Documentation snapshot 2026-09-16  \|  Implementation documentation

<!-- SOURCE-BLOCK HB11:1664 END -->

<!-- SOURCE-BLOCK HB11:1665 BEGIN -->

NetworkPolicy depends on enforcement support; connectivity policy does not replace identity, host or storage controls.

<!-- SOURCE-BLOCK HB11:1665 END -->

<!-- SOURCE-BLOCK HB11:1666 BEGIN -->

[Open official source: Kubernetes - Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

<!-- SOURCE-BLOCK HB11:1666 END -->

<!-- SOURCE-BLOCK HB11:1667 BEGIN -->

<a id="S27"></a>

[S27](77-appendix-h-primary-sources-and-implementation-references.md#S27) — NIST SP 800-88 Revision 2 - Guidelines for Media Sanitization

<!-- SOURCE-BLOCK HB11:1667 END -->

<!-- SOURCE-BLOCK HB11:1668 BEGIN -->

Final 2025  \|  Supporting technical guidance; GC tailoring required

<!-- SOURCE-BLOCK HB11:1668 END -->

<!-- SOURCE-BLOCK HB11:1669 BEGIN -->

Sanitization methods and verification; use applicable GC media-handling rules and approved technical methods.

<!-- SOURCE-BLOCK HB11:1669 END -->

<!-- SOURCE-BLOCK HB11:1670 BEGIN -->

[Open official source: NIST SP 800-88 Revision 2 - Guidelines for Media Sanitization](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

<!-- SOURCE-BLOCK HB11:1670 END -->

<!-- SOURCE-BLOCK HB11:1671 BEGIN -->

<a id="S28"></a>

[S28](77-appendix-h-primary-sources-and-implementation-references.md#S28) — Government of Canada Enterprise Architecture Framework

<!-- SOURCE-BLOCK HB11:1671 END -->

<!-- SOURCE-BLOCK HB11:1672 BEGIN -->

Public page reviewed 2026-09-16  \|  GC architecture guidance; verify applicability

<!-- SOURCE-BLOCK HB11:1672 END -->

<!-- SOURCE-BLOCK HB11:1673 BEGIN -->

Architecture governance and reuse context. Product neutrality and exit tests below are explicit handbook design decisions.

<!-- SOURCE-BLOCK HB11:1673 END -->

<!-- SOURCE-BLOCK HB11:1674 BEGIN -->

[Open official source: Government of Canada Enterprise Architecture Framework](https://www.canada.ca/en/government/system/digital-government/policies-standards/government-canada-enterprise-architecture-framework.html)

<!-- SOURCE-BLOCK HB11:1674 END -->

<!-- SOURCE-BLOCK HB11:1675 BEGIN -->

<a id="S29"></a>

[S29](77-appendix-h-primary-sources-and-implementation-references.md#S29) — ITSG-38 - Network security zoning: Design considerations for placement of services within zones

<!-- SOURCE-BLOCK HB11:1675 END -->

<!-- SOURCE-BLOCK HB11:1676 BEGIN -->

Public page reviewed 2026-09-16  \|  Cyber Centre guidance

<!-- SOURCE-BLOCK HB11:1676 END -->

<!-- SOURCE-BLOCK HB11:1677 BEGIN -->

Supporting service-placement context; source-version reconciliation belongs to the security authority.

<!-- SOURCE-BLOCK HB11:1677 END -->

<!-- SOURCE-BLOCK HB11:1678 BEGIN -->

[Open official source: ITSG-38 - Network security zoning: Design considerations for placement of services within zones](https://www.cyber.gc.ca/en/guidance/network-security-zoning-design-considerations-placement-services-within-zones-itsg-38)

<!-- SOURCE-BLOCK HB11:1678 END -->

<!-- SOURCE-BLOCK HB11:1679 BEGIN -->

<a id="S30"></a>

[S30](77-appendix-h-primary-sources-and-implementation-references.md#S30) — JSON Schema Draft 2020-12

<!-- SOURCE-BLOCK HB11:1679 END -->

<!-- SOURCE-BLOCK HB11:1680 BEGIN -->

2020-12 specification  \|  Contract specification

<!-- SOURCE-BLOCK HB11:1680 END -->

<!-- SOURCE-BLOCK HB11:1681 BEGIN -->

Machine-readable companion schemas use this dialect. Semantic admission and authorization are separate checks.

<!-- SOURCE-BLOCK HB11:1681 END -->

<!-- SOURCE-BLOCK HB11:1682 BEGIN -->

[Open official source: JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)

<!-- SOURCE-BLOCK HB11:1682 END -->

[Previous chapter](76-appendix-g-operational-records-and-decision-templates.md) · [Chapter index](README.md) · [Next chapter](78-appendix-i-glossary.md)
