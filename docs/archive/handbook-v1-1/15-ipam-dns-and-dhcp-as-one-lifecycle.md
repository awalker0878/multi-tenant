# 15. IPAM, DNS and DHCP as one lifecycle

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:281 BEGIN -->

<a id="__RefHeading___Toc13317_1645000677"></a>
<a id="sec_15"></a>

<!-- SOURCE-BLOCK HB11:281 END -->

<!-- SOURCE-BLOCK HB11:282 BEGIN -->

An authoritative IPAM service owns allocations, reservations, status and address reuse. Site, domain and tenant are allocation dimensions rather than an assumption that every tenant receives a fixed /16. Consumers request a network size or capacity class; the provider selects a prefix from the eligible scope after placement constraints are resolved. Unique addressing is the default; overlap requires an approved migration/translation design and unambiguous telemetry.

<!-- SOURCE-BLOCK HB11:282 END -->

<!-- SOURCE-BLOCK HB11:283 BEGIN -->

Allocation is transactional and idempotent by operation ID. Reserve first, commit after the dependent network is realized, and release only after routes, leases, DNS and policy are reconciled. A retry after a lost response must return the same reservation rather than allocate again. Failed requests leave an expiring reservation or an explicitly owned orphan, not an undocumented address. IPv4 and IPv6 allocations share the same resource identity but retain family-specific lifecycles.

<!-- SOURCE-BLOCK HB11:283 END -->

<!-- SOURCE-BLOCK HB11:284 BEGIN -->

DNS and DHCP profiles define authoritative zones, delegation, resolver endpoints, reverse records, lease behavior, dynamic-update authority, split-horizon requirements and retention of historical ownership. Restore and migration may change addresses while preserving logical service names. Quarantine periods depend on maximum relevant TTL, lease duration, session/NAT lifetime and evidence requirements, not a universal arbitrary delay. Address ownership history remains available for incident attribution.

<!-- SOURCE-BLOCK HB11:284 END -->

<!-- SOURCE-BLOCK HB11:285 BEGIN -->

<a id="req_IPAM_001"></a>

IPAM-001  Every managed network SHALL have an authoritative IPAM record and owner.

<!-- SOURCE-BLOCK HB11:285 END -->

<!-- SOURCE-BLOCK HB11:286 BEGIN -->

Network engineering  \|  Verify: [CT-029](73-appendix-d-conformance-test-catalogue.md#test_CT_029), [CT-030](73-appendix-d-conformance-test-catalogue.md#test_CT_030)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:286 END -->

<!-- SOURCE-BLOCK HB11:287 BEGIN -->

<a id="req_IPAM_002"></a>

IPAM-002  Overlapping address space SHALL be an explicit exception or migration pattern, not the standard tenancy model.

<!-- SOURCE-BLOCK HB11:287 END -->

<!-- SOURCE-BLOCK HB11:288 BEGIN -->

Network engineering  \|  Verify: [CT-029](73-appendix-d-conformance-test-catalogue.md#test_CT_029), [CT-061](73-appendix-d-conformance-test-catalogue.md#test_CT_061)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:288 END -->

<!-- SOURCE-BLOCK HB11:289 BEGIN -->

<a id="req_IPAM_003"></a>

IPAM-003  Address release SHOULD include quarantine/reuse controls appropriate to DNS, logging, firewall state, and incident-response requirements.

<!-- SOURCE-BLOCK HB11:289 END -->

<!-- SOURCE-BLOCK HB11:290 BEGIN -->

Network engineering  \|  Verify: [CT-013](73-appendix-d-conformance-test-catalogue.md#test_CT_013), [CT-030](73-appendix-d-conformance-test-catalogue.md#test_CT_030)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:290 END -->

<!-- SOURCE-BLOCK HB11:291 BEGIN -->

<a id="req_IPAM_004"></a>

IPAM-004  Address allocation, DNS/DHCP registration and release SHALL use idempotent operation identities, conflict detection and a dependency-aware quarantine policy; IPAM failure SHALL NOT cause guessed allocations.

<!-- SOURCE-BLOCK HB11:291 END -->

<!-- SOURCE-BLOCK HB11:292 BEGIN -->

Automation platform  \|  Verify: [CT-029](73-appendix-d-conformance-test-catalogue.md#test_CT_029), [CT-030](73-appendix-d-conformance-test-catalogue.md#test_CT_030), [CT-045](73-appendix-d-conformance-test-catalogue.md#test_CT_045), [CT-046](73-appendix-d-conformance-test-catalogue.md#test_CT_046)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:292 END -->

[Previous chapter](14-route-authority-and-safe-forwarding-compilation.md) · [Chapter index](README.md) · [Next chapter](16-ipv6-and-alternate-path-control.md)
