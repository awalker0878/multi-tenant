# References — Parent basis and external context

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<a id="__RefHeading___Toc4822_865363315"></a>
<a id="VND_app_References"></a>

Source IDs distinguish baseline-derived architecture from external context. References inform the stated design, not automatic adoption, installed compatibility or authorization. New engineering examples are local proposals. Review status below is specific to this release; inherited dates are not recertified merely by copying the source register.

<a id="VND_src_B2"></a>

## B2 — Portable Secure Hosting — Infrastructure Reference Architecture and Cross-Platform Provisioning Strategy, Draft v1.2

16 September 2026; 55-page conversation baseline \| Source baseline, not external authority

Primary parent narrative, diagrams, 30 sections, 194 requirement IDs and referenced verification catalogues.

Review status: Entire text read; three vendor diagram pages also inspected through Files; source bytes verified.

Source file: Portable\_Secure\_Hosting\_Infrastructure\_Architecture\_v1\_2.docx. Complete baseline fingerprint is in registers/release\_manifest.json.

<a id="VND_src_S03"></a>

## S03 — ITSP.70.010 - Best practices for data centre virtualization

Effective 2020-03-27 \| Cyber Centre guidance

Section 3: strong recommendation against co-locating VMs from different network security zones on the same physical hardware. Sharing requires explicit risk analysis, not a VPC claim.

Review status: Full official page reviewed: virtualization/management/storage separation context.

[Open official source — ITSP.70.010 - Best practices for data centre virtualization](https://www.cyber.gc.ca/en/guidance/cyber-centre-data-centre-virtualization-report-best-practices-data-centre-virtualization)

<a id="VND_src_S31"></a>

## S31 — Nutanix — Configuring NAT and No NAT VPCs in Flow Virtual Networking

2022-10-18; conceptual reference \| Official implementation documentation; not certification

External subnet and NAT/no-NAT concepts; historic feature limits are not asserted as current release limits.

Review status: Historic official article reviewed for NAT/no-NAT concepts only; not current product limits.

[Open official source — Nutanix — Configuring NAT and No NAT VPCs in Flow Virtual Networking](https://www.nutanix.dev/configuring-nat-and-no-nat-vpcs-in-flow-virtual-networking/)

<a id="VND_src_S33"></a>

## S33 — Broadcom — NSX Tier-0 VRF gateways

NSX 4.2 documentation reference \| Official implementation documentation; not certification

Isolated routing instances under a parent Tier-0. Official indexed excerpt inspected; full-page request returned HTTP 403. Release-specific limitations not independently verified.

Review status: Official indexed excerpts inspected; full-page retrieval unavailable. Exact release/feature limits remain unverified.

[Open official source — Broadcom — NSX Tier-0 VRF gateways](https://techdocs.broadcom.com/us/en/vmware-cis/nsx/vmware-nsx/4-2/administration-guide/tier-0-gateways/tier-0-vrf-gateways.html)

<a id="VND_src_S35"></a>

## S35 — OpenStack Neutron — OVN reference architecture

2026.1 documentation branch \| Official implementation documentation; not certification

Role separation, distributed routing and external gateway behaviour. Documentation branch is not the chosen production release.

Review status: Official 2026.1 reference branch reviewed for OVN roles/routing; not selected installed release.

[Open official source — OpenStack Neutron — OVN reference architecture](https://docs.openstack.org/neutron/2026.1/admin/ovn/refarch/refarch.html)

<a id="VND_src_S36"></a>

## S36 — OpenStack Neutron — OpenStack Networking

2026.1 documentation branch \| Official implementation documentation; not certification

Port/security-group/provider-network semantics; selected backend-specific behaviour is separately qualified.

Review status: Official 2026.1 reference branch reviewed for security-group and network semantics.

[Open official source — OpenStack Neutron — OpenStack Networking](https://docs.openstack.org/neutron/2026.1/admin/intro-os-networking.html)

[Previous chapter](7-implementation-tuple-and-decision-package.md) · [Chapter index](README.md) · [Next chapter](09-v1-4-connected-infrastructure-design-and-acceptance.md)
