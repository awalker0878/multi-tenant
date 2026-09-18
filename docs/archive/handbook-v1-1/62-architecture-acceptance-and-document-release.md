# 62. Architecture acceptance and document release

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13421_1645000677"></a>
<a id="sec_62"></a>

The original thirteen acceptance criteria are preserved as an acceptance register, with clarified scope for routine overlay lifecycle and separation of technical readiness from formal authorization. Additional criteria close the hosting, recovery, identity, supply-chain and traceability gaps. Acceptance of this document package means the specified architecture and supporting artefacts are internally complete for their declared reference scope; it does not mean the tests have run on a production system. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00), section 52\]

A production acceptance decision requires applicable criteria to pass with current evidence, unsupported capabilities to be excluded, residual risks to be authorized and named operational owners to accept the service. Candidate profiles and not-run tests intentionally remain visible. Appendix J records the changes from v1.0 and the closure status of the audit findings; Appendix C and the machine catalogue are generated from the same normative records, preventing the previous partial-index defect.

<a id="req_ACPT_001"></a>

ACPT-001  Production acceptance SHALL require current evidence for every applicable acceptance criterion, explicit exclusions and risk decisions, operational owner acceptance and a valid separately issued authorization decision.

Security authority  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S04](77-appendix-h-primary-sources-and-implementation-references.md#S04) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)  \|  new-v1.1

The evidence/authorization distinction is illustrated in Figure [5](49-evidence-controls-and-authorization-records.md#fig_evidence). The complete implementation acceptance register follows; none is marked as passed by this document release.


<a id="source-table-803"></a>

| Criterion | Acceptance outcome / verification |
| --- | --- |
| AC-01 | Routine precommissioned overlay tenant/WSD lifecycle needs no leaf/spine change; physical/bare-metal growth is a separate authorized service class.<br>Tests: CT-071 CT-072 |
| AC-02 | Cross-tenant isolation is demonstrated for every offered address family.<br>Tests: CT-001 CT-002 |
| AC-03 | Inter-zone and independent-domain communication cannot bypass the declared qualified ZIP path.<br>Tests: CT-003 CT-025 CT-080 |
| AC-04 | Workload paths do not grant access to provider management/OOB; administration follows the approved management path.<br>Tests: CT-004 CT-026 |
| AC-05 | Shared services are consumed through explicit bindings, not broad shared-subnet or management access.<br>Tests: CT-008 CT-051 |
| AC-06 | Consumers cannot create arbitrary routes, BGP peers or external attachments.<br>Tests: CT-009 CT-017 CT-033 |
| AC-07 | Equivalent IPv4/IPv6 policy is demonstrated where dual stack is offered; IPv4-only service also governs alternate IPv6 paths.<br>Tests: CT-002 CT-031 |
| AC-08 | Public ingress and Internet egress require approved service paths and attributable telemetry.<br>Tests: CT-005 CT-006 CT-063 CT-064 |
| AC-09 | Unsupported or unqualified platform capabilities fail placement rather than silently downgrade the request.<br>Tests: CT-018 |
| AC-10 | Every Ready deployment has current evidence bound to intent, profiles, source and realized state.<br>Tests: CT-049 CT-069 |
| AC-11 | Security-significant drift and expired exceptions update technical conformance/readiness without rewriting formal authorization history.<br>Tests: CT-014 CT-049 CT-058 |
| AC-12 | Offboarding removes obsolete live connectivity and authority while explicitly retaining required data/evidence obligations.<br>Tests: CT-013 CT-053 CT-059 |
| AC-13 | At least two qualified platform profiles realize equivalent portable semantics and support a representative exit rehearsal.<br>Tests: CT-016 CT-060 CT-073 |
| AC-14 | Compute/host co-residency and storage/copy isolation satisfy the actual assurance profile.<br>Tests: CT-035 CT-036 CT-037 CT-078 |
| AC-15 | Identity, privileged access, cryptography, key recovery and credential revocation meet the declared profiles.<br>Tests: CT-027 CT-028 CT-038 CT-043 CT-079 |
| AC-16 | Backup restore, site/control-plane recovery and failback meet measured service objectives without security bypass.<br>Tests: CT-051 CT-052 CT-054 CT-055 |
| AC-17 | Partial apply, concurrent operations, state recovery and stale approvals fail safely and reconcile deterministically.<br>Tests: CT-044 CT-045 CT-046 CT-048 CT-070 |
| AC-18 | Capacity, patch, image and supply-chain processes operate against the exact inventory and supported tuple.<br>Tests: CT-040 CT-041 CT-042 CT-056 CT-074 |
| AC-19 | Every active requirement has an owner, source basis and verification procedure; generated catalogues have no omissions.<br>Tests: CT-075 |
| AC-20 | Operational owners, selected controls, actual profile parameters and separate formal authorization are in place before production.<br>Tests: CT-018 CT-049 CT-062 CT-069 |

[Previous chapter](61-delivery-roadmap-and-reference-implementation.md) · [Chapter index](README.md) · [Next chapter](70-appendix-a-canonical-object-contract-and-api-surface.md)
