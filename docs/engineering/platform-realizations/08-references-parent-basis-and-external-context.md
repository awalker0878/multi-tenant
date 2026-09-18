# References — Parent basis and external context

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<!-- SOURCE-BLOCK VND:98 BEGIN -->

<a id="__RefHeading___Toc4822_865363315"></a>
<a id="VND_app_References"></a>

<!-- SOURCE-BLOCK VND:98 END -->

<!-- SOURCE-BLOCK VND:99 BEGIN -->

Source IDs distinguish baseline-derived architecture from external context. References inform the stated design, not automatic adoption, installed compatibility or authorization. New engineering examples are local proposals. Review status below is specific to this release; inherited dates are not recertified merely by copying the source register.

<!-- SOURCE-BLOCK VND:99 END -->

<!-- SOURCE-BLOCK VND:100 BEGIN -->

<a id="VND_src_B2"></a>

## B2 — Portable Secure Hosting — Infrastructure Reference Architecture and Cross-Platform Provisioning Strategy, Draft v1.2

<!-- SOURCE-BLOCK VND:100 END -->

<!-- SOURCE-BLOCK VND:101 BEGIN -->

16 September 2026; 55-page conversation baseline \| Source baseline, not external authority

<!-- SOURCE-BLOCK VND:101 END -->

<!-- SOURCE-BLOCK VND:102 BEGIN -->

Primary parent narrative, diagrams, 30 sections, 194 requirement IDs and referenced verification catalogues.

<!-- SOURCE-BLOCK VND:102 END -->

<!-- SOURCE-BLOCK VND:103 BEGIN -->

Review status: Entire text read; three vendor diagram pages also inspected through Files; source bytes verified.

<!-- SOURCE-BLOCK VND:103 END -->

<!-- SOURCE-BLOCK VND:104 BEGIN -->

Source file: Portable\_Secure\_Hosting\_Infrastructure\_Architecture\_v1\_2.docx. Complete baseline fingerprint is in registers/release\_manifest.json.

<!-- SOURCE-BLOCK VND:104 END -->

<!-- SOURCE-BLOCK VND:105 BEGIN -->

<a id="VND_src_S03"></a>

## S03 — ITSP.70.010 - Best practices for data centre virtualization

<!-- SOURCE-BLOCK VND:105 END -->

<!-- SOURCE-BLOCK VND:106 BEGIN -->

Effective 2020-03-27 \| Cyber Centre guidance

<!-- SOURCE-BLOCK VND:106 END -->

<!-- SOURCE-BLOCK VND:107 BEGIN -->

Section 3: strong recommendation against co-locating VMs from different network security zones on the same physical hardware. Sharing requires explicit risk analysis, not a VPC claim.

<!-- SOURCE-BLOCK VND:107 END -->

<!-- SOURCE-BLOCK VND:108 BEGIN -->

Review status: Full official page reviewed: virtualization/management/storage separation context.

<!-- SOURCE-BLOCK VND:108 END -->

<!-- SOURCE-BLOCK VND:109 BEGIN -->

[Open official source — ITSP.70.010 - Best practices for data centre virtualization](https://www.cyber.gc.ca/en/guidance/cyber-centre-data-centre-virtualization-report-best-practices-data-centre-virtualization)

<!-- SOURCE-BLOCK VND:109 END -->

<!-- SOURCE-BLOCK VND:110 BEGIN -->

<a id="VND_src_S31"></a>

## S31 — Nutanix — Configuring NAT and No NAT VPCs in Flow Virtual Networking

<!-- SOURCE-BLOCK VND:110 END -->

<!-- SOURCE-BLOCK VND:111 BEGIN -->

2022-10-18; conceptual reference \| Official implementation documentation; not certification

<!-- SOURCE-BLOCK VND:111 END -->

<!-- SOURCE-BLOCK VND:112 BEGIN -->

External subnet and NAT/no-NAT concepts; historic feature limits are not asserted as current release limits.

<!-- SOURCE-BLOCK VND:112 END -->

<!-- SOURCE-BLOCK VND:113 BEGIN -->

Review status: Historic official article reviewed for NAT/no-NAT concepts only; not current product limits.

<!-- SOURCE-BLOCK VND:113 END -->

<!-- SOURCE-BLOCK VND:114 BEGIN -->

[Open official source — Nutanix — Configuring NAT and No NAT VPCs in Flow Virtual Networking](https://www.nutanix.dev/configuring-nat-and-no-nat-vpcs-in-flow-virtual-networking/)

<!-- SOURCE-BLOCK VND:114 END -->

<!-- SOURCE-BLOCK VND:115 BEGIN -->

<a id="VND_src_S33"></a>

## S33 — Broadcom — NSX Tier-0 VRF gateways

<!-- SOURCE-BLOCK VND:115 END -->

<!-- SOURCE-BLOCK VND:116 BEGIN -->

NSX 4.2 documentation reference \| Official implementation documentation; not certification

<!-- SOURCE-BLOCK VND:116 END -->

<!-- SOURCE-BLOCK VND:117 BEGIN -->

Isolated routing instances under a parent Tier-0. Official indexed excerpt inspected; full-page request returned HTTP 403. Release-specific limitations not independently verified.

<!-- SOURCE-BLOCK VND:117 END -->

<!-- SOURCE-BLOCK VND:118 BEGIN -->

Review status: Official indexed excerpts inspected; full-page retrieval unavailable. Exact release/feature limits remain unverified.

<!-- SOURCE-BLOCK VND:118 END -->

<!-- SOURCE-BLOCK VND:119 BEGIN -->

[Open official source — Broadcom — NSX Tier-0 VRF gateways](https://techdocs.broadcom.com/us/en/vmware-cis/nsx/vmware-nsx/4-2/administration-guide/tier-0-gateways/tier-0-vrf-gateways.html)

<!-- SOURCE-BLOCK VND:119 END -->

<!-- SOURCE-BLOCK VND:120 BEGIN -->

<a id="VND_src_S35"></a>

## S35 — OpenStack Neutron — OVN reference architecture

<!-- SOURCE-BLOCK VND:120 END -->

<!-- SOURCE-BLOCK VND:121 BEGIN -->

2026.1 documentation branch \| Official implementation documentation; not certification

<!-- SOURCE-BLOCK VND:121 END -->

<!-- SOURCE-BLOCK VND:122 BEGIN -->

Role separation, distributed routing and external gateway behaviour. Documentation branch is not the chosen production release.

<!-- SOURCE-BLOCK VND:122 END -->

<!-- SOURCE-BLOCK VND:123 BEGIN -->

Review status: Official 2026.1 reference branch reviewed for OVN roles/routing; not selected installed release.

<!-- SOURCE-BLOCK VND:123 END -->

<!-- SOURCE-BLOCK VND:124 BEGIN -->

[Open official source — OpenStack Neutron — OVN reference architecture](https://docs.openstack.org/neutron/2026.1/admin/ovn/refarch/refarch.html)

<!-- SOURCE-BLOCK VND:124 END -->

<!-- SOURCE-BLOCK VND:125 BEGIN -->

<a id="VND_src_S36"></a>

## S36 — OpenStack Neutron — OpenStack Networking

<!-- SOURCE-BLOCK VND:125 END -->

<!-- SOURCE-BLOCK VND:126 BEGIN -->

2026.1 documentation branch \| Official implementation documentation; not certification

<!-- SOURCE-BLOCK VND:126 END -->

<!-- SOURCE-BLOCK VND:127 BEGIN -->

Port/security-group/provider-network semantics; selected backend-specific behaviour is separately qualified.

<!-- SOURCE-BLOCK VND:127 END -->

<!-- SOURCE-BLOCK VND:128 BEGIN -->

Review status: Official 2026.1 reference branch reviewed for security-group and network semantics.

<!-- SOURCE-BLOCK VND:128 END -->

<!-- SOURCE-BLOCK VND:129 BEGIN -->

[Open official source — OpenStack Neutron — OpenStack Networking](https://docs.openstack.org/neutron/2026.1/admin/intro-os-networking.html)

<!-- SOURCE-BLOCK VND:129 END -->

<!-- SOURCE-BLOCK VND:130 BEGIN -->

<!-- SOURCE-BLOCK VND:130 END -->

[Previous chapter](7-implementation-tuple-and-decision-package.md) · [Chapter index](README.md) · [Next chapter](09-v1-4-connected-infrastructure-design-and-acceptance.md)
