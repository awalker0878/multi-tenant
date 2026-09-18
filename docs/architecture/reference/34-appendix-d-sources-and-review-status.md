# Appendix D — Sources and review status

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3706_865363315"></a>
<a id="RA_app_D"></a>

Source IDs distinguish baseline-derived architecture from external context. References inform the stated design, not automatic adoption, installed compatibility or authorization. New engineering examples are local proposals. Review status below is specific to this release; inherited dates are not recertified merely by copying the source register.

<a id="RA_src_B1"></a>

## B1 — Portable Multi-Tenant Secure Hosting Handbook, Draft v1.1

September 2026, 105 pages \| User-provided/generated conversation baseline

Primary revision basis. Requirement/test records and section lineage retained. The content is architecture guidance, not proof of live conformance.

Review status: Inherited baseline reference; not independently reverified in this release.

<a id="RA_src_B2"></a>

## B2 — Portable Secure Hosting — Infrastructure Reference Architecture and Cross-Platform Provisioning Strategy, Draft v1.2

16 September 2026; 55-page conversation baseline \| Source baseline, not external authority

Primary parent narrative, diagrams, 30 sections, 194 requirement IDs and referenced verification catalogues.

Review status: Entire text read; three vendor diagram pages also inspected through Files; source bytes verified.

Source file: Portable\_Secure\_Hosting\_Infrastructure\_Architecture\_v1\_2.docx. Complete baseline fingerprint is in registers/release\_manifest.json.

<a id="RA_src_S01"></a>

## S01 — ITSP.80.022 - Baseline security requirements for network security zones, version 2.0

Effective 2021-01-12 \| Cyber Centre guidance

Sections 2-4 and annexes A-F. Zone definitions, joint ZIP authority and management boundaries. Architecture requirements in this handbook are local translations, not quotations.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — ITSP.80.022 - Baseline security requirements for network security zones, version 2.0](https://www.cyber.gc.ca/en/guidance/baseline-security-requirements-network-security-zones-version-20-itsp80022)

<a id="RA_src_S02"></a>

## S02 — ITSP.80.023 - Cloud network security zones

Effective 2023-06-12 \| Cyber Centre guidance

Companion to ITSP.80.022; cloud ZIP functions, isolated MZ approach and control/data-plane distinctions. Limited to Unclassified/Protected A/Protected B context.

Review status: Full official page reviewed: cloud-zone scope, management and ZIP context.

[Open official source — ITSP.80.023 - Cloud network security zones](https://www.cyber.gc.ca/en/guidance/cloud-network-security-zones-itsp80023)

<a id="RA_src_S03"></a>

## S03 — ITSP.70.010 - Best practices for data centre virtualization

Effective 2020-03-27 \| Cyber Centre guidance

Section 3: strong recommendation against co-locating VMs from different network security zones on the same physical hardware. Sharing requires explicit risk analysis, not a VPC claim.

Review status: Full official page reviewed: virtualization/management/storage separation context.

[Open official source — ITSP.70.010 - Best practices for data centre virtualization](https://www.cyber.gc.ca/en/guidance/cyber-centre-data-centre-virtualization-report-best-practices-data-centre-virtualization)

<a id="RA_src_S05"></a>

## S05 — ITSP.10.033 - Security and privacy controls and assurance activities catalogue: Foreword, overview, introduction

Effective 2026-03-31 \| Cyber Centre control catalogue

Explicitly supersedes ITSG-33 Annex 3A. Canadian-specific 100-series identifiers move to 400-series. Source families are starting points for tailoring, not automatic control equivalence.

Review status: Full official page reviewed: 2026 catalogue transition; not a selected-control assessment.

[Open official source — ITSP.10.033 - Security and privacy controls and assurance activities catalogue: Foreword, overview, introduction](https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction)

<a id="RA_src_S10"></a>

## S10 — ITSP.40.111 - Cryptographic algorithms for Unclassified, Protected A and Protected B information, version 5

Effective 2026-05-29 \| Cyber Centre cryptographic guidance

Use a versioned cryptographic profile and migration inventory; a fixed legacy algorithm list is insufficient.

Review status: Full official page reviewed: versioned algorithm guidance; no product validation asserted.

[Open official source — ITSP.40.111 - Cryptographic algorithms for Unclassified, Protected A and Protected B information, version 5](https://www.cyber.gc.ca/en/guidance/cryptographic-algorithms-unclassified-protected-protected-b-information-itsp40111)

<a id="RA_src_S11"></a>

## S11 — Event Logging Guidance

Public page reviewed 2026-09-16 \| GC operational guidance

Centralized protected event collection, event classes and operational ownership. Local retention examples are not attributed as GC-mandated durations.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — Event Logging Guidance](https://www.canada.ca/en/government/system/digital-government/online-security-privacy/cyber-security-guidance-policy/event-logging-guidance.html)

<a id="RA_src_S13"></a>

## S13 — Terraform - Providers within modules

Documentation snapshot 2026-09-16 \| Implementation documentation

Provider configuration in root modules; explicit provider passing and aliases where required.

Review status: Full official page reviewed: root provider configuration and module passing.

[Open official source — Terraform - Providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers)

<a id="RA_src_S14"></a>

## S14 — Terraform - Dependency lock file

Documentation snapshot 2026-09-16 \| Implementation documentation

Locks provider selections/checksums, not remote module selections; pin module versions or immutable revisions separately.

Review status: Full official page reviewed: provider lockfile versus remote module versioning.

[Open official source — Terraform - Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)

<a id="RA_src_S17"></a>

## S17 — Nutanix Terraform provider - official repository

Version information inherited from the prior review; no current provider selection made \| Implementation documentation, not certification

Provider provenance reference only. Earlier README version notes are not a current or qualified implementation tuple.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — Nutanix Terraform provider - official repository](https://github.com/nutanix/terraform-provider-nutanix)

<a id="RA_src_S18"></a>

## S18 — VMware NSX Terraform provider - official repository

Documentation snapshot 2026-09-16 \| Implementation documentation, not certification

Provider provenance and NSX realization context; exact product/provider tuple must be qualified before placement.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — VMware NSX Terraform provider - official repository](https://github.com/vmware/terraform-provider-nsxt)

<a id="RA_src_S20"></a>

## S20 — RFC 8212 - Default External BGP route propagation behavior without policies

2017 \| IETF technical specification

Import/export policy requirements inform the provider-owned fabric profile; confirm vendor implementation behavior.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — RFC 8212 - Default External BGP route propagation behavior without policies](https://www.rfc-editor.org/info/rfc8212/)

<a id="RA_src_S21"></a>

## S21 — RFC 7432 - BGP MPLS-Based Ethernet VPN

2015; update/errata chain reviewed \| IETF technical specification

Foundational EVPN signaling and multihoming concepts; it is not by itself a VXLAN conformance claim.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — RFC 7432 - BGP MPLS-Based Ethernet VPN](https://datatracker.ietf.org/doc/html/rfc7432)

<a id="RA_src_S22"></a>

## S22 — RFC 8365 - A network virtualization overlay solution using EVPN

2018 \| IETF technical specification

EVPN overlay use. Qualify extensions and interoperability rather than assuming equal product feature sets.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — RFC 8365 - A network virtualization overlay solution using EVPN](https://datatracker.ietf.org/doc/html/rfc8365)

<a id="RA_src_S23"></a>

## S23 — RFC 8200 - Internet Protocol, Version 6 specification

2017 \| IETF technical specification

IPv6 transport foundation; security semantics and operational profiles remain explicit.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — RFC 8200 - Internet Protocol, Version 6 specification](https://datatracker.ietf.org/doc/html/rfc8200)

<a id="RA_src_S24"></a>

## S24 — RFC 4890 - Recommendations for filtering ICMPv6 messages in firewalls

2007 \| IETF guidance

Avoid blanket ICMPv6 denial that breaks required protocol operation; filter by the selected profile.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — RFC 4890 - Recommendations for filtering ICMPv6 messages in firewalls](https://datatracker.ietf.org/doc/html/rfc4890)

<a id="RA_src_S25"></a>

## S25 — Kubernetes - Multi-tenancy

Documentation snapshot 2026-09-16 \| Implementation documentation

Namespace isolation is not a complete hostile-tenant boundary; compute/control-plane choices require threat analysis.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — Kubernetes - Multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)

<a id="RA_src_S26"></a>

## S26 — Kubernetes - Network Policies

Documentation snapshot 2026-09-16 \| Implementation documentation

NetworkPolicy depends on enforcement support; connectivity policy does not replace identity, host or storage controls.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — Kubernetes - Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

<a id="RA_src_S27"></a>

## S27 — NIST SP 800-88 Revision 2 - Guidelines for Media Sanitization

Final 2025 \| Supporting technical guidance; GC tailoring required

Sanitization methods and verification; use applicable GC media-handling rules and approved technical methods.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — NIST SP 800-88 Revision 2 - Guidelines for Media Sanitization](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

<a id="RA_src_S31"></a>

## S31 — Nutanix — Configuring NAT and No NAT VPCs in Flow Virtual Networking

2022-10-18; conceptual reference \| Official implementation documentation; not certification

External subnet and NAT/no-NAT concepts; historic feature limits are not asserted as current release limits.

Review status: Historic official article reviewed for NAT/no-NAT concepts only; not current product limits.

[Open official source — Nutanix — Configuring NAT and No NAT VPCs in Flow Virtual Networking](https://www.nutanix.dev/configuring-nat-and-no-nat-vpcs-in-flow-virtual-networking/)

<a id="RA_src_S32"></a>

## S32 — Nutanix — Enabling Flow Virtual Networking on AHV

2022-12-12; conceptual reference \| Official implementation documentation; not certification

Prism/Flow enablement and management dependency context; exact deployment/version requires current product qualification.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — Nutanix — Enabling Flow Virtual Networking on AHV](https://www.nutanix.dev/enabling-nutanix-flow-virtual-networking-on-ahv/)

<a id="RA_src_S33"></a>

## S33 — Broadcom — NSX Tier-0 VRF gateways

NSX 4.2 documentation reference \| Official implementation documentation; not certification

Isolated routing instances under a parent Tier-0. Official indexed excerpt inspected; full-page request returned HTTP 403. Release-specific limitations not independently verified.

Review status: Official indexed excerpts inspected; full-page retrieval unavailable. Exact release/feature limits remain unverified.

[Open official source — Broadcom — NSX Tier-0 VRF gateways](https://techdocs.broadcom.com/us/en/vmware-cis/nsx/vmware-nsx/4-2/administration-guide/tier-0-gateways/tier-0-vrf-gateways.html)

<a id="RA_src_S34"></a>

## S34 — VMware — Multi-tiered routing with NSX-T

2018-02-20; conceptual reference \| Official implementation documentation; not certification

Tier-0/Tier-1 and distributed/service-routing concepts; not a current compatibility or licensing statement.

Review status: Inherited baseline reference; not independently reverified in this release.

[Open official source — VMware — Multi-tiered routing with NSX-T](https://blogs.vmware.com/networkvirtualization/2018/02/nsx-t-multi-tiered-routing-architecture.html/)

<a id="RA_src_S35"></a>

## S35 — OpenStack Neutron — OVN reference architecture

2026.1 documentation branch \| Official implementation documentation; not certification

Role separation, distributed routing and external gateway behaviour. Documentation branch is not the chosen production release.

Review status: Official 2026.1 reference branch reviewed for OVN roles/routing; not selected installed release.

[Open official source — OpenStack Neutron — OVN reference architecture](https://docs.openstack.org/neutron/2026.1/admin/ovn/refarch/refarch.html)

<a id="RA_src_S36"></a>

## S36 — OpenStack Neutron — OpenStack Networking

2026.1 documentation branch \| Official implementation documentation; not certification

Port/security-group/provider-network semantics; selected backend-specific behaviour is separately qualified.

Review status: Official 2026.1 reference branch reviewed for security-group and network semantics.

[Open official source — OpenStack Neutron — OpenStack Networking](https://docs.openstack.org/neutron/2026.1/admin/intro-os-networking.html)

<a id="RA_src_S37"></a>

## S37 — OpenStack Nova — Host aggregates

2026.1 documentation branch \| Official implementation documentation; not certification

Scheduling and Placement/aggregate controls; labels do not alone establish isolation.

Review status: Official 2026.1 reference branch reviewed for aggregate/scheduling context.

[Open official source — OpenStack Nova — Host aggregates](https://docs.openstack.org/nova/2026.1/admin/aggregates.html)

<a id="RA_src_S38"></a>

## S38 — RFC 7766 — DNS Transport over TCP: Implementation Requirements

March 2016 \| IETF standards-track reference

General-purpose DNS TCP support and fallback; not a blanket firewall policy for all DNS roles.

Review status: Official full text reviewed.

[Open official source — RFC 7766 — DNS Transport over TCP: Implementation Requirements](https://www.rfc-editor.org/rfc/rfc7766)

<a id="RA_src_S39"></a>

## S39 — ITSP.40.062 — Guidance on securely configuring network protocols

Official web guidance reviewed 16 September 2026 \| Cyber Centre guidance; applicability and selected configuration require adoption

Secure protocol configuration as distinct from algorithm selection.

Review status: Official full page reviewed.

[Open official source — ITSP.40.062 — Guidance on securely configuring network protocols](https://www.cyber.gc.ca/en/guidance/guidance-securely-configuring-network-protocols-itsp40062)

[Previous chapter](33-appendix-c-architecture-terminology.md) · [Chapter index](README.md) · [Next chapter](35-appendix-e-linked-engineering-knowledge-and-decision-map.md)
