# Appendix B — Infrastructure interface schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:435 BEGIN -->

<a id="__RefHeading___Toc3702_865363315"></a>
<a id="RA_app_B"></a>

<!-- SOURCE-BLOCK RA:435 END -->

<!-- SOURCE-BLOCK RA:436 BEGIN -->

Each deployed interface has an owner, endpoint membership, routing/security authority, protocol/address-family profile, failure behaviour and lifecycle. The schedule below defines the interface classes to instantiate; the site design fills their actual addresses, ports, capacity, identifiers and release-specific parameters. It is not a software API schema.

<!-- SOURCE-BLOCK RA:436 END -->

<!-- SOURCE-BLOCK RA:437 BEGIN -->


<a id="source-table-437"></a>

| ID / interface | Connection and boundary | Required design record |
| --- | --- | --- |
| IF-01  Underlay | Leaf/spine or equivalent physical routed adjacency | ASN/address scope, permitted neighbours/prefixes, multipath, control protection and convergence |
| IF-02  Platform transport | Tunnel endpoints within a vendor realization over IP transport | Eligible hosts, encapsulation/MTU, address family, isolation and failure behaviour |
| IF-03  Domain edge attachment | Native domain gateway to its isolated security-service handoff | Independent routing context, allowed prefixes, NAT if used, return path and reuse policy |
| IF-04  Logical ZIP | Approved relationship between two security authorities | Both domain owners, rules/inspection, policy precedence, logging, sessions, HA and management |
| IF-05  Privileged management | Authorized administration/automation to named infrastructure interfaces | Identity scope, trusted path, certificates, audit and emergency procedure |
| IF-06  OOB recovery | Independent authorized access to hardware console/management | Physical dependencies, permitted devices, recovery credentials and test evidence |
| IF-07  Platform data transport | Hypervisor/controller/storage or live-mobility endpoints | Membership, physical/logical separation, keys, performance and recovery restrictions |
| IF-08  Shared-service consumption | Tenant/domain to entitled service endpoint | Protocol, direction, identity/data scope, zone boundary and service dependencies |
| IF-09  Provisioning handoff | One infrastructure owner/work package to its dependent package | Resource reference, eligibility/capacity, ready state, version and ownership; no shared broad credentials |
| IF-10  Inter-site service | Replication, recovery or explicit cross-site access | Data consistency, bandwidth/latency, encryption, failure ownership, fencing and activation |
| IF-11  External access | Public/enterprise/partner boundary to a declared exposure service | External authority, entry path, protection, names/certificates, allowed flows and withdrawal |
| IF-12  Operational evidence | Infrastructure event/measurement to approved collection and review | Source identity/time, protected transport, tenant attribution, access, retention and loss behaviour |

<!-- SOURCE-BLOCK RA:437 END -->

<!-- SOURCE-BLOCK RA:438 BEGIN -->

<!-- SOURCE-BLOCK RA:438 END -->

<!-- SOURCE-BLOCK RA:439 BEGIN -->

Do not infer an interface’s trust from a product label. A provider network can carry a tenant escape path; a management API can change a workload without any guest route; a virtual disk can reach storage without using the guest NIC. The topology and actual authority determine which controls must be implemented and tested.

<!-- SOURCE-BLOCK RA:439 END -->

[Previous chapter](31-appendix-a-revision-scope-and-baseline-traceability.md) · [Chapter index](README.md) · [Next chapter](33-appendix-c-architecture-terminology.md)
