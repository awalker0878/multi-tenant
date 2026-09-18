# 61. Delivery roadmap and reference implementation

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:788 BEGIN -->

<a id="__RefHeading___Toc13419_1645000677"></a>
<a id="sec_61"></a>

<!-- SOURCE-BLOCK HB11:788 END -->

<!-- SOURCE-BLOCK HB11:789 BEGIN -->

Build a small but end-to-end reference implementation before expanding platform count. The initial laboratory contains two tenants, each with OZ and RZ logical domains and site-local instances, zone-specific host pools, a qualified data ZIP service, isolated MZ/OOB, DNS/time/logging/identity/backup/key services, IPv4 and controlled IPv6 testing, and no direct public exposure. Add a PAZ/public-ingress fixture separately to test that service rather than forcing every workload to have a PAZ.

<!-- SOURCE-BLOCK HB11:789 END -->

<!-- SOURCE-BLOCK HB11:790 BEGIN -->


<a id="source-table-790"></a>

| Stage | Deliverable and exit gate |
| --- | --- |
| 1 — Adopt the contract | Agree sources, categorization, profiles, authority, schema and requirements; document adoption is not deployment approval |
| 2 — Qualify foundations | Commission OOB/fabric/platform and protected bootstrap; prove routing/management isolation, versions and capacity |
| 3 — Qualify edges/services | Build two-endpoint ZIP relationships, bindings, key/identity/log/backup services and failure behavior |
| 4 — First complete platform | Implement native adapters and controller workflow; provision two tenants and demonstrate positive/negative, partial-failure and retirement tests |
| 5 — Operational assurance | Protect evidence/state/source, exercise restore and site/control recovery, establish drift/patch/incident processes |
| 6 — Second platform and exit | Realize the same portable request on a second qualified platform; test data/application exit and policy equivalence |
| 7 — Production adoption | Independent review, actual service parameters/owners, residual-risk decisions and formal authorization before production readiness |
| 8 — Expand and maintain | Add the third/future platform, measured scale and automated placement; requalify material changes and publish service limitations |

<!-- SOURCE-BLOCK HB11:790 END -->

<!-- SOURCE-BLOCK HB11:791 BEGIN -->

For each platform, capture an inventory snapshot and exact qualification tuple, then repeat the same contract and core test set. Separately test any shared-attachment or distributed-ZIP design because those paths are the most likely place for “no switch churn” to conflict with isolation. The first success is a fully evidenced small system, not a maximal feature count or a green empty Terraform root.

<!-- SOURCE-BLOCK HB11:791 END -->

<!-- SOURCE-BLOCK HB11:792 BEGIN -->

The companion validation suite verifies schemas, sample contracts, requirement/test/source completeness and internal document-package consistency. It does not contact real switches, hypervisors, clouds, KMS or backup services. Implementers execute Appendix D against their authorized target environments and retain the resulting evidence. None of those live test outcomes are pre-populated as passes in this release.

<!-- SOURCE-BLOCK HB11:792 END -->

<!-- SOURCE-BLOCK HB11:793 BEGIN -->

<a id="req_DEL_001"></a>

DEL-001  The reference implementation SHALL demonstrate two-tenant isolation, controlled zone transitions, protected management, service bindings, recovery and retirement on a qualified first platform before scale expansion.

<!-- SOURCE-BLOCK HB11:793 END -->

<!-- SOURCE-BLOCK HB11:794 BEGIN -->

Delivery owner  \|  Verify: [CT-001](73-appendix-d-conformance-test-catalogue.md#test_CT_001), [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-004](73-appendix-d-conformance-test-catalogue.md#test_CT_004), [CT-008](73-appendix-d-conformance-test-catalogue.md#test_CT_008), [CT-013](73-appendix-d-conformance-test-catalogue.md#test_CT_013), [CT-052](73-appendix-d-conformance-test-catalogue.md#test_CT_052), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:794 END -->

<!-- SOURCE-BLOCK HB11:795 BEGIN -->

<a id="req_DEL_002"></a>

DEL-002  Multi-platform portability claims SHALL be supported by the same intent/core conformance outcomes on at least two qualified implementations and by a representative data/application exit rehearsal.

<!-- SOURCE-BLOCK HB11:795 END -->

<!-- SOURCE-BLOCK HB11:796 BEGIN -->

Delivery owner  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060), [CT-073](73-appendix-d-conformance-test-catalogue.md#test_CT_073)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:796 END -->

[Previous chapter](60-architecture-review-and-onboarding-gates.md) · [Chapter index](README.md) · [Next chapter](62-architecture-acceptance-and-document-release.md)
