# 10. Zone classes, external domains and adjacency

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13307_1645000677"></a>
<a id="sec_10"></a>

The controlled workload-zone vocabulary is PAZ, OZ, RZ and HRZ; MZ is a provider-controlled management zone. ZIP is a boundary relationship, not a workload zone. PZ and REZ are represented through ExternalDomain objects because their authority differs from the managed internal domain. REZ means Restricted Extranet Zone, not “remote extranet”; it requires a defined trusted-partner relationship. ITSP.80.022 treats ordinary extranet access through PAZ differently from REZ, and does not label connections between GC departments/agencies as REZ. \[[S01](77-appendix-h-primary-sources-and-implementation-references.md#S01), sections 2.1.6 and 3.2.2\]

The following is this handbook’s conservative baseline adjacency policy, not a reproduction of every possible government topology. “ZIP” authorizes creation of a jointly governed boundary only; default traffic remains deny. A service that terminates a connection and originates a separate downstream connection is modeled as two flows, not an implicit end-to-end route through an intermediate zone. Non-baseline adjacencies require an explicit architecture and security decision.


<a id="source-table-218"></a>

| Relationship | Baseline realization | Required condition |
| --- | --- | --- |
| PZ → PAZ | Public boundary ZIP and declared ingress/egress service | Exposure profile, certificates/DNS, owner and telemetry |
| PAZ ↔ OZ | Explicit data-path ZIP | Approved application flow; no unrestricted internal transit |
| OZ ↔ RZ | Explicit data-path ZIP | Joint authority and constrained services |
| RZ ↔ HRZ | Dedicated/high-assurance-qualified ZIP | Specific threat/control analysis; HRZ does not enable classified scope |
| REZ ↔ OZ or RZ | Partner boundary ZIP | Authenticated endpoints, agreement and appropriate trust analysis |
| PZ → OZ/RZ/HRZ or MZ | Prohibited direct attachment | Use the authorized public/service or remote-management path |
| MZ ↔ managed target | Management-specific ZIP/control path | Dedicated privileged administration; not workload transit |
| Same class, different domain | Explicit boundary/service relation | Independent ownership and default deny still apply |
| Other adjacency | Not enabled by the base profile | Approved profile extension and complete enforcement evidence |

An ExternalDomain records type, authority, trust basis, agreements, authenticated endpoints, location constraints, approved service directions and revocation behavior. “Enterprise” and “cloud interconnect” describe connection purpose, not automatic trust. A private circuit does not convert a partner into an internal tenant or create a route to every tenant. The controller validates both graph topology and the effective forwarding/enforcement paths.

<a id="req_ZONE_001"></a>

ZONE-001  Internal instance zoneClass SHALL be limited to PAZ, OZ, RZ, HRZ or provider-controlled MZ; external PZ/REZ relationships SHALL use ExternalDomain with explicit authority and trust metadata.

Security authority  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-076](73-appendix-d-conformance-test-catalogue.md#test_CT_076)  \|  Basis: [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  new-v1.1

<a id="req_ZONE_002"></a>

ZONE-002  Every requested adjacency SHALL be evaluated against the versioned zone policy before allocation; being permitted to create a ZIP SHALL NOT grant any traffic by default.

Automation platform  \|  Verify: [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  new-v1.1

[Previous chapter](9-security-domains-and-site-platform-instances.md) · [Chapter index](README.md) · [Next chapter](11-zip-architecture-and-joint-boundary-authority.md)
