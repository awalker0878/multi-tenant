# 35. Nutanix implementation profile

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:500 BEGIN -->

<a id="__RefHeading___Toc13361_1645000677"></a>
<a id="sec_35"></a>

<!-- SOURCE-BLOCK HB11:500 END -->

<!-- SOURCE-BLOCK HB11:501 BEGIN -->

The candidate Nutanix realization maps tenant administration to approved project/RBAC scopes, logical security domains to controlled metadata, and domain instances to qualified Flow Virtual Networking/VPC constructions. Networks are overlay subnets; mandatory workload policy uses the qualified Flow security mechanism; external attachments connect toward the declared ZIP or service edge. Project ownership, VPC routing, categories and security policy are distinct control functions, not interchangeable isolation proofs.

<!-- SOURCE-BLOCK HB11:501 END -->

<!-- SOURCE-BLOCK HB11:502 BEGIN -->

The official Nutanix provider repository reviewed for this revision identifies release 2.4.2 and lists v2 resources including VPCs, subnets, PBR, routes and network security policy. It also publishes platform compatibility notes. This is a documentation reference only: the installed AOS, Prism Central, Flow versions and licensed features must be confirmed before selecting a provider version or claiming support. A v2 resource name alone does not establish that every requested feature is available on the target. \[[S17](77-appendix-h-primary-sources-and-implementation-references.md#S17)\]

<!-- SOURCE-BLOCK HB11:502 END -->

<!-- SOURCE-BLOCK HB11:503 BEGIN -->


<a id="source-table-503"></a>

| Portable element | Candidate realization | Qualification focus |
| --- | --- | --- |
| Tenant / domain | Project/RBAC plus provider-owned security metadata; VPC or approved routing construction | Tenant cannot alter global administration or mandatory selectors |
| Network / flow | Overlay subnet, scoped Flow policy and explicit edge flow | Default routing, label precedence and same-host enforcement |
| EdgeAttachment | Qualified external subnet, gateway/routing/PBR and security-edge context | Shared external connectivity, connected routes, NAT/PBR and return symmetry |
| Compute / data | Qualified VM, image, affinity, storage and protection functions | Co-residency, lifecycle support, copies, encryption and recovery |
| Automation | Pinned official provider and documented API tuple | Readiness polling, idempotency, updates, imports, deletion and secret handling |

<!-- SOURCE-BLOCK HB11:503 END -->

<!-- SOURCE-BLOCK HB11:504 BEGIN -->

Commission reusable attachment capacity where isolation permits, but do not assume that multiple VPCs on a common external subnet are isolated from each other. CT-023 is a mandatory gate for sharing. Protect provider-owned categories and baseline rules from tenant modification; validate effective policy and the enforcement path before connecting workloads. Capture Prism/Flow readiness rather than treating asynchronous API acceptance as complete. HCI co-residency analysis covers controller/storage services as well as VM scheduling.

<!-- SOURCE-BLOCK HB11:504 END -->

<!-- SOURCE-BLOCK HB11:505 BEGIN -->

<a id="req_NUT_001"></a>

NUT-001  New Nutanix automation SHOULD use current supported v2/v4-backed provider resources where those resources satisfy the requirement; legacy resources require an explicit compatibility rationale.

<!-- SOURCE-BLOCK HB11:505 END -->

<!-- SOURCE-BLOCK HB11:506 BEGIN -->

Platform engineering  \|  Verify: [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S17](77-appendix-h-primary-sources-and-implementation-references.md#S17)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:506 END -->

<!-- SOURCE-BLOCK HB11:507 BEGIN -->

<a id="req_NUT_002"></a>

NUT-002  Nutanix VPC internal routing SHALL NOT be used to bypass a required inter-zone ZIP.

<!-- SOURCE-BLOCK HB11:507 END -->

<!-- SOURCE-BLOCK HB11:508 BEGIN -->

Platform engineering  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023), [CT-024](73-appendix-d-conformance-test-catalogue.md#test_CT_024)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:508 END -->

<!-- SOURCE-BLOCK HB11:509 BEGIN -->

<a id="req_NUT_003"></a>

NUT-003  Provider-managed categories/metadata used for security SHALL be protected from tenant modification.

<!-- SOURCE-BLOCK HB11:509 END -->

<!-- SOURCE-BLOCK HB11:510 BEGIN -->

Platform engineering  \|  Verify: [CT-020](73-appendix-d-conformance-test-catalogue.md#test_CT_020), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:510 END -->

<!-- SOURCE-BLOCK HB11:511 BEGIN -->

<a id="req_NUT_004"></a>

NUT-004  The Nutanix profile SHALL qualify the actual AOS/Prism/Flow/provider tuple and external-attachment behavior; unresolved licensing, routing, policy precedence or asynchronous realization limitations SHALL block the affected capability.

<!-- SOURCE-BLOCK HB11:511 END -->

<!-- SOURCE-BLOCK HB11:512 BEGIN -->

Platform engineering  \|  Verify: [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023), [CT-045](73-appendix-d-conformance-test-catalogue.md#test_CT_045), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S17](77-appendix-h-primary-sources-and-implementation-references.md#S17)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:512 END -->

[Previous chapter](34-portability-dimensions-and-platform-qualification.md) · [Chapter index](README.md) · [Next chapter](36-vmware-and-nsx-implementation-profile.md)
