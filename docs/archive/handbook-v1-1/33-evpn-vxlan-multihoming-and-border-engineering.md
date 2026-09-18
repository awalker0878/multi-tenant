# 33. EVPN/VXLAN, multihoming and border engineering

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13357_1645000677"></a>
<a id="sec_33"></a>

EVPN/VXLAN is an optional transport/physical-attachment realization, not a required consumer construct. Distinguish the IP underlay from EVPN signaling and overlay forwarding. RFC 7432 supplies foundational EVPN signaling concepts; RFC 8365 addresses network-virtualization overlay use. Product qualification records the implemented extensions and applicable updates/errata rather than claiming that the base RFC number proves full multi-vendor interoperability. \[[S21](77-appendix-h-primary-sources-and-implementation-references.md#S21); [S22](77-appendix-h-primary-sources-and-implementation-references.md#S22)\]

The fabric authority allocates RD/RT and VNI/VRF identifiers with collision detection and defined administrative scope. Route imports are explicit; a common route target must not join independent security domains. The profile specifies supported EVPN route types, L2/L3 gateway placement, ARP/ND suppression, MAC mobility/duplication controls, BUM handling, route scale and border policy. A physical VRF is introduced only when the fabric is the authorized L3 realization for a real domain, not because the function is called backup, transit or platform.


<a id="source-table-480"></a>

| Design area | Required decision |
| --- | --- |
| Underlay/overlay routing | eBGP/other qualified underlay, overlay peering model, address families and control-plane independence |
| Route import/export | Per-domain permitted RT/prefix sets, default-deny policy, maximum routes and summary boundaries |
| Gateway placement | Anycast/local gateway ownership, symmetric or other qualified IRB model, edge/service attachment paths |
| Host multihoming | Choose qualified MLAG or EVPN multihoming; identify peer-link/ESI, split-brain and orphan-port behavior |
| Border interoperability | Explicit standard BGP/VLAN/routed handoff with tested MTU, communities, next hops and failure modes |
| Overlay on overlay | Avoid needless encapsulation stacking; if offered, budget MTU, offload, ECMP entropy and troubleshooting |

Do not assume that two vendors interoperate as one MLAG pair; ordinary inter-vendor L3/BGP or other documented interfaces are the preferred boundary. EVPN multihoming has a different control model from vendor-specific MLAG. Stateful security paths require special attention to asymmetric routing and active/active behavior. RFC 8212 supports explicit external BGP import/export policy; the implementation must verify the vendor’s actual defaults and configured behavior. \[[S20](77-appendix-h-primary-sources-and-implementation-references.md#S20)\]

Commissioning tests include single link/leaf loss, peer-link/keepalive failure, route withdrawal, MAC move, MTU/PMTU, unauthorized route import and control-plane load. A layer-2 storage transport network can exist without inventing a fabric security-zone VRF, but its host/port membership and non-routing constraints remain governed. Firmware upgrade tests recheck the exact interface behavior used by attached HCI platforms.

<a id="req_EVPN_001"></a>

EVPN-001  When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped; unapproved route imports SHALL be denied.

Network engineering  \|  Verify: [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-033](73-appendix-d-conformance-test-catalogue.md#test_CT_033), [CT-072](73-appendix-d-conformance-test-catalogue.md#test_CT_072)  \|  Basis: [S20](77-appendix-h-primary-sources-and-implementation-references.md#S20) / [S21](77-appendix-h-primary-sources-and-implementation-references.md#S21) / [S22](77-appendix-h-primary-sources-and-implementation-references.md#S22)  \|  new-v1.1

<a id="req_EVPN_002"></a>

EVPN-002  Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior; vendor-specific MLAG interoperability SHALL NOT be assumed.

Network engineering  \|  Verify: [CT-024](73-appendix-d-conformance-test-catalogue.md#test_CT_024), [CT-032](73-appendix-d-conformance-test-catalogue.md#test_CT_032), [CT-034](73-appendix-d-conformance-test-catalogue.md#test_CT_034)  \|  Basis: [S21](77-appendix-h-primary-sources-and-implementation-references.md#S21) / [S22](77-appendix-h-primary-sources-and-implementation-references.md#S22)  \|  new-v1.1

[Previous chapter](32-physical-fabric-foundation-and-commissioning.md) · [Chapter index](README.md) · [Next chapter](34-portability-dimensions-and-platform-qualification.md)
