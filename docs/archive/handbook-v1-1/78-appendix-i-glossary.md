# Appendix I — Glossary

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:1683 BEGIN -->

<a id="__RefHeading___Toc13451_1645000677"></a>
<a id="app_I"></a>

<!-- SOURCE-BLOCK HB11:1683 END -->

<!-- SOURCE-BLOCK HB11:1684 BEGIN -->


<a id="source-table-1684"></a>

| Term | Definition |
| --- | --- |
| Admission | Decision that a versioned request is syntactically and semantically allowed within approved authority and profiles. |
| Artifact digest | Cryptographic identity used to detect changes to a specific artifact; integrity identity alone is not proof of trust or approval. |
| Assurance Profile | Local policy selecting isolation, evidence and verification requirements; not itself an official security assurance level. |
| Authorization | Decision by the designated authority permitting operation under specified scope, risk and conditions. |
| Availability impact | Security categorization of consequences from lost availability; separate from service uptime and recovery objectives. |
| BFD | Bidirectional Forwarding Detection; an optional qualified rapid failure-detection mechanism. |
| BGP | Border Gateway Protocol; provider-controlled routing protocol with explicit policy. |
| BMC | Baseboard management controller; privileged hardware management component. |
| Candidate / Qualified | Capability lifecycle states; Candidate has no production qualification. Qualified requires exact versions, evidence, limits and approval. |
| C/I/A | Confidentiality, integrity and availability; independent security categorization dimensions. |
| CI/CD | Continuous integration and delivery pipeline, with authority and release gates appropriate to the change. |
| CMDB | Configuration management database or equivalent authoritative service/resource inventory. |
| Co-residency | Sharing physical or administrative resources among workloads, zones or tenants; each shared layer has its own threat boundary. |
| Control family | Grouping of controls in a specified catalogue; a family mapping is not a complete control selection or assessment. |
| DFW | Distributed firewall; native enforcement distributed across supported workload/host locations. |
| Domain | Logical zone class and security authority; instances are site/platform realizations. |
| ECMP | Equal-cost multipath forwarding; path diversity does not guarantee stateful inspection symmetry. |
| Edge Attachment | Provider-internal contract joining an instance to an authorized boundary with routing, identity, MTU and HA requirements. |
| EvidenceRecord | Manifest binding intent, realized objects, tests, versions, exceptions and protected artifacts. |
| EVPN | Ethernet VPN; BGP signaling mechanisms used with qualified transport and overlay profiles. |
| Exposure | Explicit public, egress, enterprise or partner service relationship; never an implicit default route. |
| ExternalDomain | Boundary object for PUBLIC, qualified REZ partner, enterprise or cloud-interconnect authority. |
| Finalizer | Lifecycle guard preventing resource deletion until named dependencies/obligations are resolved. |
| Flow Intention / FlowIntent | Portable communication outcome between identities or services, compiled into native controls. |
| Fencing | Preventing a failed or ambiguous writer from continuing to modify data before another writer is promoted. |
| HA | High availability under a declared, tested failure model. |
| HRZ | Highly Restricted Zone; a controlled internal zone, not automatic authorization for classified information. |
| IaC | Infrastructure as code: versioned desired configuration actuated through controlled tools. |
| IAM | Identity and access management for human, workload, service and automation identities. |
| IPAM | Authoritative IP address management, with leases, owners, reservations and reuse controls. |
| ISSIP | Information System Security Implementation Process, retained as lifecycle lineage from ITSG-33. |
| JIT / JEA | Just-in-time and just-enough administration; minimize duration and scope of privilege. |
| KMS / HSM | Key management service / hardware security module; products and operating modes require applicable assurance. |
| L2VNI / L3VNI | VXLAN network identifiers used by an approved implementation; not consumer security-zone names. |
| MLAG | Multi-chassis link aggregation; implementation-specific HA behavior requiring split-brain and interoperability tests. |
| MTU | Maximum transmission unit; verify end-to-end path limits including all encapsulations. |
| MZ | Management Zone, an isolated administration security domain; not synonymous with a transport network. |
| NAT | Network address translation; not a complete isolation or identity mechanism. |
| ND / RA | IPv6 Neighbor Discovery / Router Advertisement; govern local-link behavior and unauthorized advertisements. |
| OOB | Out-of-band management transport, ideally independently reachable during production-network failure. |
| OZ | Operations Zone for authorized operational workloads under the selected security profile. |
| PAZ | Public Access Zone, mediating authorized public/external service interactions. |
| PAM | Privileged access management, including approval, controlled sessions, recording and break-glass. |
| PBMM | Protected B, Medium integrity and Medium availability-impact profile context; not a topology or uptime commitment. |
| PBR | Policy-based routing, whose failure/return-path behavior must preserve required inspection. |
| PZ | Public Zone; represented as external PUBLIC authority in this contract. |
| RD / RT | Route distinguisher / route target; allocated and controlled by the provider, never consumer-defined trust. |
| REZ | Restricted Extranet Zone; a specific trusted-partner relationship, modeled as an external domain. |
| RPO / RTO | Recovery point objective / recovery time objective, measured against the defined recovered service boundary. |
| RZ | Restricted Zone for authorized sensitive or critical systems/services under the selected profile. |
| Saga-style workflow | Journaled multi-stage operation with scoped compensating actions; not an atomic multi-system transaction. |
| SDI | Security Domain Instance: a site/platform-specific realization of a logical Security Domain. |
| Service Binding | Authorized consumer relationship to a published provider endpoint and profile. |
| Service Ready | Current desired generation, qualified implementation, required evidence and authorization conditions all satisfied. |
| SLO | Service-level objective with an explicit measurement window, boundary and accounting policy. |
| Terraform state | Tool representation of managed objects; protected authority/blast-radius boundary, not the complete source of service truth. |
| Tenant Namespace | Administrative ownership, entitlement and quota scope; not a security zone or a shared network. |
| Tombstone | Retained stable identity and lifecycle evidence for a retired object. |
| VRF | Virtual routing and forwarding context; a mechanism, not an enterprise security-zone definition. |
| VXLAN | Virtual extensible LAN encapsulation; used only with a qualified underlay/overlay profile. |
| WSD | Workload Security Domain: primary workload lifecycle and desired security/service intent object. |
| ZIP | Zone Interface Point: jointly governed boundary function between two domains; can be a qualified composed/distributed realization. |

<!-- SOURCE-BLOCK HB11:1684 END -->

[Previous chapter](77-appendix-h-primary-sources-and-implementation-references.md) · [Chapter index](README.md) · [Next chapter](79-appendix-j-audit-closure-migration-and-release-checks.md)
