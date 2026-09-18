# Appendix C — Architecture terminology

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3704_865363315"></a>
<a id="RA_app_C"></a>


<a id="source-table-441"></a>

| Term | Meaning in this document |
| --- | --- |
| Tenant / provider | Consumer administrative scope / operator of the hosting infrastructure and its shared services; provider does not mean a particular manufacturer |
| Hosting cell | Provider unit of qualified capacity, lifecycle and fault containment; not necessarily a vendor cluster or Nova cell |
| WSD | Workload Security Domain: bounded hosting-service requirements, lifecycle and ownership for related resources |
| Security Domain / Instance | Logical zone/authority boundary / its site-and-platform realization |
| PAZ / OZ / RZ / HRZ | Public Access / Operations / Restricted / Highly Restricted Zone. HRZ is an explicitly approved extension, not a default cloud capability |
| PZ / REZ / MZ | Public Zone / Restricted Extranet Zone / Management Zone; public and partner authorities are external to the local domain realization |
| ZIP | Zone Interface Point: the governed boundary relationship and security functions between two zones |
| OOB | Out-of-band management: a separately designed access/recovery transport, not merely a management VLAN label |
| Underlay / overlay | Physical IP transport / a logical network carried over transport; different vendor overlays are not automatically interoperable |
| eBGP / ASN / ECMP | External Border Gateway Protocol / autonomous system number / equal-cost multipath forwarding |
| EVPN / VXLAN | Ethernet VPN signalling / Virtual Extensible LAN encapsulation; qualified together where used |
| VLAN / VNI / RD / RT | Virtual LAN / VXLAN network identifier / route distinguisher / route target; implementation allocations owned by the provider |
| MLAG | Multi-chassis link aggregation; a qualified attachment mechanism distinct from EVPN multihoming |
| HCI / CVM | Hyperconverged infrastructure / Nutanix Controller VM; controller/storage sharing must be included in isolation analysis |
| SDN / DFW / OVN | Software-defined networking / distributed firewall / Open Virtual Network, a possible Neutron backend |
| IPAM / DHCP / DNS | IP address management / dynamic host configuration / domain name services, managed as a consistent lifecycle |
| IAM / PAM / PKI | Identity and access management / privileged access management / public key infrastructure |
| KMS / HSM | Key management service / hardware security module; key use, administration, recovery and destruction are separate authorities |
| SLO / RTO / RPO | Service-level objective / recovery time objective / recovery point objective; require actual adopted and measured parameters |
| Service binding / exposure | Scoped use of a provider service / an approved relationship with an external access domain |
| Provisioning work package | An owned infrastructure change scope with prerequisites, execution authority, handoff and completion evidence |
| Qualification / authorization | Evidence that a specific implementation meets an offered profile / a separately issued acceptance of system security risk |
| Portable / composite / migrated | Equivalent deployment on another stack / one delivery using several stacks or shared services / transfer and cutover of actual workload/data state |

[Previous chapter](32-appendix-b-infrastructure-interface-schedule.md) · [Chapter index](README.md) · [Next chapter](34-appendix-d-sources-and-review-status.md)
