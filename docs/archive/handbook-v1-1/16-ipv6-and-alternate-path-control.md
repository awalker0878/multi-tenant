# 16. IPv6 and alternate-path control

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:293 BEGIN -->

<a id="__RefHeading___Toc13319_1645000677"></a>
<a id="sec_16"></a>

<!-- SOURCE-BLOCK HB11:293 END -->

<!-- SOURCE-BLOCK HB11:294 BEGIN -->

The contract supports explicit ipv4-only, ipv6-only or dual-stack address-family modes, but each offered mode requires separate qualification. IPv6 is not an unchecked Boolean that promises platform support. Dual-stack admission checks routing, ZIP policy, service endpoints, observability, DNS, recovery and the complete attachment path. IPv4-only service still needs a documented treatment of IPv6 local control traffic and unapproved encapsulation/transition paths.

<!-- SOURCE-BLOCK HB11:294 END -->

<!-- SOURCE-BLOCK HB11:295 BEGIN -->

The IPv6 profile specifies prefix allocation, gateway/RA/DHCPv6 behavior, neighbor discovery, source validation, router-advertisement protection, extension-header/fragment policy and required ICMPv6. Do not copy a blanket IPv4-style ICMP deny that prevents necessary IPv6 operation or path-MTU discovery. Link-local connectivity is scoped to the segment and must not create an ungoverned administration path. Qualify both positive protocol operation and negative security paths. \[[S23](77-appendix-h-primary-sources-and-implementation-references.md#S23); [S24](77-appendix-h-primary-sources-and-implementation-references.md#S24)\]

<!-- SOURCE-BLOCK HB11:295 END -->

<!-- SOURCE-BLOCK HB11:296 BEGIN -->

Operational records carry address family and the stable domain/WSD identity. NAT, if present, is recorded as translation rather than identity; original and translated tuples are attributable. IPv6-only service must declare any IPv4-only dependency and an approved mediation pattern; unsupported family conversion is rejected instead of routed through an unmanaged appliance.

<!-- SOURCE-BLOCK HB11:296 END -->

<!-- SOURCE-BLOCK HB11:297 BEGIN -->

<a id="req_IPV6_001"></a>

IPV6-001  Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists.

<!-- SOURCE-BLOCK HB11:297 END -->

<!-- SOURCE-BLOCK HB11:298 BEGIN -->

Network engineering  \|  Verify: [CT-002](73-appendix-d-conformance-test-catalogue.md#test_CT_002), [CT-031](73-appendix-d-conformance-test-catalogue.md#test_CT_031), [CT-032](73-appendix-d-conformance-test-catalogue.md#test_CT_032)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:298 END -->

<!-- SOURCE-BLOCK HB11:299 BEGIN -->

<a id="req_IPV6_002"></a>

IPV6-002  Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service.

<!-- SOURCE-BLOCK HB11:299 END -->

<!-- SOURCE-BLOCK HB11:300 BEGIN -->

Platform engineering  \|  Verify: [CT-002](73-appendix-d-conformance-test-catalogue.md#test_CT_002), [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-031](73-appendix-d-conformance-test-catalogue.md#test_CT_031)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:300 END -->

<!-- SOURCE-BLOCK HB11:301 BEGIN -->

<a id="req_IPV6_003"></a>

IPV6-003  Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies; unsupported family combinations SHALL be rejected.

<!-- SOURCE-BLOCK HB11:301 END -->

<!-- SOURCE-BLOCK HB11:302 BEGIN -->

Network engineering  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-031](73-appendix-d-conformance-test-catalogue.md#test_CT_031), [CT-032](73-appendix-d-conformance-test-catalogue.md#test_CT_032)  \|  Basis: [S23](77-appendix-h-primary-sources-and-implementation-references.md#S23) / [S24](77-appendix-h-primary-sources-and-implementation-references.md#S24)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:302 END -->

[Previous chapter](15-ipam-dns-and-dhcp-as-one-lifecycle.md) · [Chapter index](README.md) · [Next chapter](17-shared-services-and-explicit-service-bindings.md)
