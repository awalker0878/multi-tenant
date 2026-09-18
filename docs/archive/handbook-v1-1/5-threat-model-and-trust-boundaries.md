# 5. Threat model and trust boundaries

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:165 BEGIN -->

<a id="__RefHeading___Toc13295_1645000677"></a>
<a id="sec_5"></a>

<!-- SOURCE-BLOCK HB11:165 END -->

<!-- SOURCE-BLOCK HB11:166 BEGIN -->

Assume tenant workloads may be compromised or malicious, administrators may make mistakes, vendor defaults may be permissive, and a platform or automation dependency may become unavailable. A shared private network is not a trust assertion. Model the credible compromise of an individual workload, tenant identity, automation runner, host, security edge, backup identity, shared service and software-supply-chain component separately. The design is intended to constrain each compromise without claiming immunity to a provider-wide privileged breach.

<!-- SOURCE-BLOCK HB11:166 END -->

<!-- SOURCE-BLOCK HB11:167 BEGIN -->


<a id="source-table-167"></a>

| Threat or failure | Boundary/control response | Residual issue to assess |
| --- | --- | --- |
| Cross-tenant or cross-zone lateral movement | Independent domain identity, deny baseline and verified ZIP/microsegmentation paths | Shared-host vulnerability and shared edge failure exposure |
| Compromised administrator or runner | Separate credentials/state, short-lived grants, peer approval and signed operation journal | Emergency authority, identity-provider and vault compromise |
| Data theft or destructive backup action | Storage scope, encryption, independent recovery authority and protected copies | Key custody, data-copy lineage and retention conflicts |
| Overlay or route-policy error | Provider-controlled route graph, explicit adjacency, data-plane negative tests | Shared attachment, NAT hairpin and distributed enforcement gaps |
| Controller outage or partial apply | Deny/quarantine before exposure, journaled recovery and generation checks | Orphaned allocations, stale policy and inconsistent inventory |
| Site loss or common dependency loss | Prequalified recovery, independent bootstrap and fencing | KMS/DNS/time/IdP dependencies and correlated failure domains |
| Supplier or support compromise | Provenance, controlled update path and time-bound support access | Jurisdiction, diagnostics export and hidden support dependencies |

<!-- SOURCE-BLOCK HB11:167 END -->

<!-- SOURCE-BLOCK HB11:168 BEGIN -->

A threat model includes the attack surface and the business consequences, then allocates controls and tests. Where an assurance profile permits shared hardware, record exactly which threat is mitigated by logical isolation and which residual risks remain. The existence of multiple VPCs, projects or VRFs alone does not resolve hypervisor, storage, management or supply-chain trust. \[[S03](77-appendix-h-primary-sources-and-implementation-references.md#S03); [S08](77-appendix-h-primary-sources-and-implementation-references.md#S08)\]

<!-- SOURCE-BLOCK HB11:168 END -->

<!-- SOURCE-BLOCK HB11:169 BEGIN -->

<a id="req_THR_001"></a>

THR-001  Each platform qualification and material WSD change SHALL include a threat/failure analysis that identifies trust boundaries, privileged actors, dependency failures, residual risks and applicable tests.

<!-- SOURCE-BLOCK HB11:169 END -->

<!-- SOURCE-BLOCK HB11:170 BEGIN -->

Security authority  \|  Verify: [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S03](77-appendix-h-primary-sources-and-implementation-references.md#S03) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) / [S08](77-appendix-h-primary-sources-and-implementation-references.md#S08)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:170 END -->

[Previous chapter](4-categorization-and-policy-profiles.md) · [Chapter index](README.md) · [Next chapter](6-canonical-model-and-service-planes.md)
