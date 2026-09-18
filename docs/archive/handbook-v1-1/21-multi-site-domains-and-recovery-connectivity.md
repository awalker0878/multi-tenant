# 21. Multi-site domains and recovery connectivity

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13329_1645000677"></a>
<a id="sec_21"></a>

A WSD can span sites while each site retains independent domain instances, address allocations, security-edge enforcement and failure domains. L2 stretch is not the baseline. Prefer routed replication and service-level failover with explicit security, consistency and capacity requirements. A stretch exception must describe partition behavior, split-brain prevention, quorum location, recovery ownership and the impact on both security and availability.

An availability zone or site label is not proof of physical independence. Record common power, facility, uplinks, control clusters, storage, KMS, identity, time and logging dependencies. Replication is a declared flow with a data owner; it is not an unrestricted management or migration network. A recovery site inherits the WSD policy and required controls, not a temporary emergency exemption.

Recovery includes fencing the old writer, selecting a known data-consistency point, reconstructing domain/network/service dependencies, restoring identity/certificates, validating the recovered workload, and only then changing exposure/DNS. Failback is a separate planned migration with new data ownership and consistency checks. See section 53 for the ordered recovery runbooks.

<a id="req_SITE_001"></a>

SITE-001  Security Domain Instances SHOULD be site-local by default.

Platform engineering  \|  Verify: [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054), [CT-055](73-appendix-d-conformance-test-catalogue.md#test_CT_055)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SITE_002"></a>

SITE-002  Layer-2 stretch across sites SHALL require a documented application/availability requirement and failure-domain analysis.

Architecture authority  \|  Verify: [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SITE_003"></a>

SITE-003  Recovery-site connectivity SHALL be pre-authorized and tested; emergency recovery SHALL NOT depend on ad hoc route leaking.

Recovery operations  \|  Verify: [CT-052](73-appendix-d-conformance-test-catalogue.md#test_CT_052), [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SITE_004"></a>

SITE-004  Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints; writer fencing and failback ownership SHALL be proven before production recovery is offered.

Recovery operations  \|  Verify: [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-038](73-appendix-d-conformance-test-catalogue.md#test_CT_038), [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054), [CT-061](73-appendix-d-conformance-test-catalogue.md#test_CT_061)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](20-provider-internal-edge-attachment-contract.md) · [Chapter index](README.md) · [Next chapter](24-part-iii-portable-hosting-services.md)
