# 20. Provisioning model and infrastructure work packages

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3678_865363315"></a>
<a id="RA_s_020"></a>

Provisioning is the controlled realization of the preceding architecture. It has three different scopes: commissioning shared capacity, allocating a tenant environment within that capacity, and changing or retiring the delivered service. They use different authority, timing and failure boundaries. Zero-touch applies to routine approved allocations and changes inside an already commissioned service envelope; it does not mean that racking equipment, establishing trust or approving new security boundaries disappears.


<a id="source-table-292"></a>

| Work package | Infrastructure it owns | Primary execution responsibility |
| --- | --- | --- |
| P0 — Bootstrap and trust | Initial privileged access, minimum independent services, trusted tooling and recovery material | Platform/foundation bootstrap process |
| P1 — Physical foundation | OOB, transport, physical routing and platform/edge attachment capacity | Network and hardware automation; supported configuration interfaces |
| P2 — Platform commissioning | Cluster/control installation, storage, overlay, eligible pools and protected management | Vendor/distribution installer and lifecycle tooling, supplemented by supported APIs |
| P3 — Security and common services | Edge contexts/capacity, identity, keys, names, logging, backup and service interfaces | Service owners using their scoped management tools/providers |
| P4 — Tenant and domain allocation | Entitlements, placement, address reservations, native domain/network objects and mandatory policy | Cross-platform provisioning workflow and qualified Terraform modules/APIs |
| P5 — Workload and service activation | VMs, volumes, service bindings, approved routes/exposure and operational handover | Platform plus edge/data-service execution under separate authority |
| P6 — Change and retirement | Resize, repair, migration, restoration, access withdrawal and disposal | Lifecycle owner with dependent platform/service work packages |

Each package publishes a bounded handoff: resource identity, eligible service classes, capacity, permitted use, dependencies and readiness. The next package consumes that handoff rather than modifying its predecessor’s infrastructure through a convenient privileged credential. An attachment identifier can be shared; the entire security-edge state file and its administrative credentials need not be.

![Provisioning dependencies and separate execution authorities Bootstrap enables physical foundation and vendor-platform commissioning. Common security and service foundations plus qualified platform capacity enable tenant/domain allocation. Platform-specific compute/network resources and independently managed edge, IPAM, DNS, backup and key resources converge at verification and activation. Terraform is an execution mechanism within these work packages, not the owner of architecture or authorization.](../../assets/diagrams/2446c0c4b447e0c26b3b.png)

<a id="fig_provisioning"></a>

Figure 8. Provisioning dependencies and separate execution authorities

## Functional responsibilities, not a prescribed application

The provisioning service needs request intake, authorization, placement checks, reservation, ordered execution, status tracking and evidence. These can be supplied by an existing service catalogue, change workflow, automation platform and inventory system. This reference does not prescribe microservices, a database schema, message bus, programming language or a new custom controller. The implementation must preserve the functions and authority boundaries regardless of tool choice.

Architecture and security owners define eligible templates, profiles and connectivity patterns. Platform and service owners implement native modules and interfaces. A delivery workflow coordinates approved changes, while each package executes with scoped authority. Risk approval and technical verification remain distinct from automated execution. Routine scale changes can be pre-authorized within limits; new exposure, trust relationships or isolation changes require the appropriate authority.

The work-package graph includes explicit bootstrap exceptions to avoid circular commissioning. P2 installation may initially consume accepted P0 name/time/trust services; P2 platform service acceptance and P3 shared-service acceptance are completed together before P4 allocation. Temporary dependencies have named owners and verified steady-state transfer. PROV §§1–2 provide the handoffs and dependency-cut review.

Related engineering: [PROV §1 — Provisioning scopes, ownership and accepted handoffs](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)

[Previous chapter](19-physical-workloads-and-future-platform-extensions.md) · [Chapter index](README.md) · [Next chapter](21-day-0-bootstrap-and-physical-commissioning.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0013 — Compose provisioning across separate platform and service authorities](../../adr/0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

<!-- END GENERATED DECISION LINKS -->
