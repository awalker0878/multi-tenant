# 60. Architecture review and onboarding gates

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:782 BEGIN -->

<a id="__RefHeading___Toc13417_1645000677"></a>
<a id="sec_60"></a>

<!-- SOURCE-BLOCK HB11:782 END -->

<!-- SOURCE-BLOCK HB11:783 BEGIN -->

The following review is a release checklist, not a substitute for the detailed requirement catalogue. Each answer links to a named object, owner, test or evidence artifact. “Not applicable” includes rationale and approving authority. An implementation that cannot supply an item remains Candidate or blocked for that offered service class.

<!-- SOURCE-BLOCK HB11:783 END -->

<!-- SOURCE-BLOCK HB11:784 BEGIN -->


<a id="source-table-784"></a>

| Gate | Required evidence |
| --- | --- |
| Ownership and scope | Tenant/service/data/security owners, supported category, application/provider responsibility split and lifecycle |
| Intent and model | Validated WSD, logical domains/instances, network ownership, flow/service/exposure references and no vendor IDs in consumer intent |
| Security and placement | Separate C/I/A categorization, approved profiles, co-residency/data-location constraints, selected controls and current authorization conditions |
| Network and management | Valid zone adjacency/ZIPs, management/OOB separation, route authority, dual-stack posture and edge attachments |
| Compute, data and identity | Qualified host/image/storage/crypto/key/backup identity controls and copy lineage |
| Readiness and reliability | Defined service SLO/RTO/RPO, dependency/failure model, capacity reserves, operational ownership and tested restore |
| Automation and assurance | Immutable approved plan, scoped state/credentials, conformance results, current evidence and active exceptions |
| Lifecycle and exit | Safe change/deletion, retention/sanitization, migration/exit method and inventory integration |

<!-- SOURCE-BLOCK HB11:784 END -->

<!-- SOURCE-BLOCK HB11:785 BEGIN -->

The final readiness decision checks that the observed generation equals the requested generation, all mandatory conditions are satisfied, required test evidence is current, profiles/capabilities are Qualified and authorization conditions are met. The owner accepts the delivered service scope. A deployment can exist in Quarantined or Degraded state without being Service Ready; this permits safe troubleshooting without falsifying its status.

<!-- SOURCE-BLOCK HB11:785 END -->

<!-- SOURCE-BLOCK HB11:786 BEGIN -->

<a id="req_ONB_001"></a>

ONB-001  Onboarding SHALL verify ownership, complete intent/profiles, current qualification/authorization conditions, operational readiness and lifecycle obligations before Service Ready is granted.

<!-- SOURCE-BLOCK HB11:786 END -->

<!-- SOURCE-BLOCK HB11:787 BEGIN -->

Service management  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:787 END -->

[Previous chapter](59-change-exceptions-and-risk-decisions.md) · [Chapter index](README.md) · [Next chapter](61-delivery-roadmap-and-reference-implementation.md)
