# ADR-0036 — Require initial operational and recovery readiness before production activation

**Status:** Proposed<br>
**Accountable role:** Service management / Service owner / Continuity management<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `RD14-04`<br>
**Source chapters:** [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [QUAL §1](../assurance/site-qualification/1-from-proposed-architecture-to-accepted-service.md) · [DEL §3](../governance/delivery-framework/3-apply-gate-dependencies-rather-than-numerical-order.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Reading gate numbers as a sequence can incorrectly put production activation before the operating and recovery evidence needed to support the offered service.

## Decision

Treat gates as dependency types. Production G3 requires current platform/service qualification, valid operating authority and applicable initial G4 operational/recovery readiness. Separate later recurring exercises from initial prerequisites.

## Alternatives and source limitations

Restricted authorized non-production fixtures may precede G2 to generate qualification evidence. They are not production-ready environments and do not waive initial readiness.

## Consequences

The same dependency applies to public and internal production access. A recorded test specification or promised future recovery drill is not current readiness evidence.

## Engineering and implementation obligations

Identify initial versus continuing obligations, the exact offered service promise, actual recovery results, named owners and the reversible activation/post-activation checks.

## Requirement and code traceability

[ONB-001](../assurance/requirements.md#ONB-001) · [REL-001](../assurance/requirements.md#REL-001) · [REC-002](../assurance/requirements.md#REC-002) · [ACPT-001](../assurance/requirements.md#ACPT-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [docs/COMMISSIONING.md](../COMMISSIONING.md)
- [tools/recovery_review.py](../../tools/recovery_review.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

No production activation or authorization is issued by an ADR extraction; actual initial readiness remains a target-specific acceptance gate.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
