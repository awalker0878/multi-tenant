# ADR-0036 — Require initial operational and recovery readiness before production activation

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `RD14-04`<br>
**Source chapters:** [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [QUAL §1](../assurance/site-qualification/1-from-proposed-architecture-to-accepted-service.md) · [DEL §3](../governance/delivery-framework/3-apply-gate-dependencies-rather-than-numerical-order.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

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

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [docs/COMMISSIONING.md](../COMMISSIONING.md)
- [tools/recovery_review.py](../../tools/recovery_review.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

No production activation or authorization is issued by an ADR extraction; actual initial readiness remains a target-specific acceptance gate.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
