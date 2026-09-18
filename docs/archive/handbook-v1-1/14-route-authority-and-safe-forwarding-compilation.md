# 14. Route Authority and safe forwarding compilation

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13315_1645000677"></a>
<a id="sec_14"></a>

Route Authority is a provider-controlled compiler, not a consumer route editor. Its input is the authorized graph of domains, IPAM allocations, ZIP adjacencies, service bindings, external exposure, site reachability and placement. Its output is an explicit forwarding plan, import/export policy and provenance explaining why each route exists. The compiler checks recursive next hops, connected paths, summaries and default routes as well as explicit static routes.

A flow permission and a route solve different problems. A route must not imply permission to all reachable destinations; a firewall rule must not hide a broad or unintended forwarding path. The controller compares both the intended graph and the realized RIB/FIB/enforcement state. Avoid summarization that accidentally includes another tenant or security domain. Prefer precise service routes and controlled endpoint publishing over broad shared supernets.


<a id="source-table-271"></a>

| Consumer request | Provider-controlled result |
| --- | --- |
| Use the approved identity service | Resolved endpoint, direction, service profile, route and policy references |
| Expose HTTPS | Approved public boundary, PAZ ingress, certificate/DNS and backend flow |
| Enable controlled egress | Destination/protocol profile, mediated route and attribution; not arbitrary 0/0 |
| Replicate to recovery site | Authorized replication endpoints, capacity reservation and recovery security path |
| Migrate for a bounded window | Time-limited connection, explicit routes, telemetry and automated revocation |

A transit routing mechanism can exist inside a qualified implementation, but an undifferentiated transit VRF is not the enterprise security model. No generic hub or shared attachment may become an alternate inter-zone path. Route installation and removal follow dependency-safe ordering; a failed route operation leaves the workload unexposed or restricted, not reachable through an improvised default.

<a id="req_RTE_001"></a>

RTE-001  Routes, route imports/exports, and BGP adjacencies SHALL be provider-controlled outputs of authorized intent.

Network engineering  \|  Verify: [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-033](73-appendix-d-conformance-test-catalogue.md#test_CT_033)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_RTE_002"></a>

RTE-002  A generalized shared transit VRF SHALL NOT be used as a default inter-zone routing mechanism.

Network engineering  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_RTE_003"></a>

RTE-003  Temporary migration or transition routes SHALL have explicit scope, approval, expiry, telemetry, and automated teardown.

Network engineering  \|  Verify: [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-077](73-appendix-d-conformance-test-catalogue.md#test_CT_077)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_RTE_004"></a>

RTE-004  Route compilation SHALL validate connected routes, recursive next hops, summaries, NAT/PBR interactions and all enabled address families; realized forwarding SHALL be compared with the approved graph before exposure.

Network engineering  \|  Verify: [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023), [CT-024](73-appendix-d-conformance-test-catalogue.md#test_CT_024), [CT-031](73-appendix-d-conformance-test-catalogue.md#test_CT_031)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](13-platform-overlays-and-enforcement-ownership.md) · [Chapter index](README.md) · [Next chapter](15-ipam-dns-and-dhcp-as-one-lifecycle.md)
