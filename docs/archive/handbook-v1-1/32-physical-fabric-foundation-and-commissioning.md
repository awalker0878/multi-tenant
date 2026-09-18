# 32. Physical fabric foundation and commissioning

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:462 BEGIN -->

<a id="__RefHeading___Toc13355_1645000677"></a>
<a id="sec_32"></a>

<!-- SOURCE-BLOCK HB11:462 END -->

<!-- SOURCE-BLOCK HB11:463 BEGIN -->

The default large-site foundation is a routed L3 Clos with ECMP. A smaller site may use another explicitly qualified routed topology when its capacity and failure requirements do not justify a full Clos. The fabric supplies stable transport, platform/security-edge attachments and any legitimate physical routing domains. It does not own ordinary WSD firewall policy or expose leaf/spine configuration to workload consumers.

<!-- SOURCE-BLOCK HB11:463 END -->

<!-- SOURCE-BLOCK HB11:464 BEGIN -->

Commission the management path, addressing, underlay, routing policy, telemetry, platform transport and edge attachment pools before tenant onboarding. Treat hardware expansion, new physical attachment classes and maintenance as foundation changes under separate authority. The original absolute “no fabric changes” statement is narrowed to routine lifecycle within precommissioned overlay service capacity; bare-metal/fabric-routed classes publish their separate foundation workflow.

<!-- SOURCE-BLOCK HB11:464 END -->

<!-- SOURCE-BLOCK HB11:465 BEGIN -->


<a id="source-table-465"></a>

| Foundation item | Required engineering decision / evidence |
| --- | --- |
| Physical inventory and links | Supported platform/NIC/optic/firmware tuple, port role, speed, redundancy and documented physical failure domains |
| Underlay addressing and routing | Loopback/link allocation authority, ASN policy, IPv4/IPv6 families, permitted neighbors and import/export policy |
| Control-plane protection | Authenticated administration, routing authentication where supported/required, rate limits, maximum prefixes and alerts |
| Transport MTU | End-to-end workload MTU plus every encapsulation layer; PMTU and nested-overlay tests where offered |
| Failure and maintenance | Convergence target, drain/reload sequence, peer-link/multihoming behavior and rollback criteria |
| Operational evidence | Configuration digests, versioned inventory, route snapshots, port/error/optics telemetry and qualified capacity |

<!-- SOURCE-BLOCK HB11:465 END -->

<!-- SOURCE-BLOCK HB11:466 BEGIN -->

Hardware and operational management stay reachable only through approved management paths. No native VLAN or permissive trunk is assumed acceptable for tenant isolation. Unused interfaces are disabled or bound to an explicit secure commissioning profile. Network configuration has an authoritative source, drift detection and safe rollback; state synchronization between MLAG peers or controllers is itself a protected dependency.

<!-- SOURCE-BLOCK HB11:466 END -->

<!-- SOURCE-BLOCK HB11:467 BEGIN -->

![Routed L3/ECMP fabric connects platform and security-service attachment paths. Tenant state stays in the qualified overlay where available. Inter-domain traffic traverses the security edge. OOB and management access remain a separately controlled foundation path.](../../assets/diagrams/36c12748242558618b11.png)

<!-- SOURCE-BLOCK HB11:467 END -->

<!-- SOURCE-BLOCK HB11:468 BEGIN -->

<a id="fig_fabric"></a>

Figure 3. Stable provider fabric and independently governed attachments

<!-- SOURCE-BLOCK HB11:468 END -->

<!-- SOURCE-BLOCK HB11:469 BEGIN -->

<a id="req_FAB_001"></a>

FAB-001  Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes; foundation growth and fabric-routed service classes SHALL use separately authorized workflows.

<!-- SOURCE-BLOCK HB11:469 END -->

<!-- SOURCE-BLOCK HB11:470 BEGIN -->

Network engineering  \|  Verify: [CT-071](73-appendix-d-conformance-test-catalogue.md#test_CT_071), [CT-072](73-appendix-d-conformance-test-catalogue.md#test_CT_072)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  revised-v1.0

<!-- SOURCE-BLOCK HB11:470 END -->

<!-- SOURCE-BLOCK HB11:471 BEGIN -->

<a id="req_FAB_002"></a>

FAB-002  A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain.

<!-- SOURCE-BLOCK HB11:471 END -->

<!-- SOURCE-BLOCK HB11:472 BEGIN -->

Network engineering  \|  Verify: [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-072](73-appendix-d-conformance-test-catalogue.md#test_CT_072)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:472 END -->

<!-- SOURCE-BLOCK HB11:473 BEGIN -->

<a id="req_FAB_003"></a>

FAB-003  Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF.

<!-- SOURCE-BLOCK HB11:473 END -->

<!-- SOURCE-BLOCK HB11:474 BEGIN -->

Architecture authority  \|  Verify: [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-072](73-appendix-d-conformance-test-catalogue.md#test_CT_072)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:474 END -->

<!-- SOURCE-BLOCK HB11:475 BEGIN -->

<a id="req_FAB_004"></a>

FAB-004  The fabric profile SHALL define addressing/routing authority, control-plane protection, MTU, fault convergence, management isolation, maintenance and measured scale before platform commissioning.

<!-- SOURCE-BLOCK HB11:475 END -->

<!-- SOURCE-BLOCK HB11:476 BEGIN -->

Network engineering  \|  Verify: [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026), [CT-032](73-appendix-d-conformance-test-catalogue.md#test_CT_032), [CT-033](73-appendix-d-conformance-test-catalogue.md#test_CT_033), [CT-034](73-appendix-d-conformance-test-catalogue.md#test_CT_034)  \|  Basis: [S20](77-appendix-h-primary-sources-and-implementation-references.md#S20) / [S21](77-appendix-h-primary-sources-and-implementation-references.md#S21) / [S22](77-appendix-h-primary-sources-and-implementation-references.md#S22)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:476 END -->

[Previous chapter](35-part-iv-infrastructure-and-platform-realization.md) · [Chapter index](README.md) · [Next chapter](33-evpn-vxlan-multihoming-and-border-engineering.md)
