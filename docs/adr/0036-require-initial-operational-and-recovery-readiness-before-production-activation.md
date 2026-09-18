# ADR-0036 — Require initial operational and recovery readiness before production activation

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `RD14-04`<br>
**Source chapters:** [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [QUAL §1](../assurance/site-qualification/1-from-proposed-architecture-to-accepted-service.md) · [DEL §3](../governance/delivery-framework/3-apply-gate-dependencies-rather-than-numerical-order.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

Reading gate numbers as a sequence can incorrectly put production activation before the operating and recovery evidence needed to support the offered service.

## Decision recorded in the source

Treat gates as dependency types. Production G3 requires current platform/service qualification, valid operating authority and applicable initial G4 operational/recovery readiness. Separate later recurring exercises from initial prerequisites.

## Alternatives and limits recorded in the source

Restricted authorized non-production fixtures may precede G2 to generate qualification evidence. They are not production-ready environments and do not waive initial readiness.

## Consequences

The same dependency applies to public and internal production access. A recorded test specification or promised future recovery drill is not current readiness evidence.

## Engineering and implementation obligations

Identify initial versus continuing obligations, the exact offered service promise, actual recovery results, named owners and the reversible activation/post-activation checks.

## Requirement and code traceability

[ONB-001](../assurance/requirements.md#ONB-001) · [REL-001](../assurance/requirements.md#REL-001) · [REC-002](../assurance/requirements.md#REC-002) · [ACPT-001](../assurance/requirements.md#ACPT-001)

Related implementation areas are traceability targets, not proof of complete implementation:

- [docs/COMMISSIONING.md](../COMMISSIONING.md)
- [tools/recovery_review.py](../../tools/recovery_review.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

No production activation or authorization is issued by an ADR extraction; actual initial readiness remains a target-specific acceptance gate.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
