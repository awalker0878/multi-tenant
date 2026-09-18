# ADR-0017 — Separate reference adoption, technical qualification and authorization

**Status:** Proposed<br>
**Accountable role:** Architecture, assurance and service-acceptance authorities<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-15`<br>
**Source chapters:** [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [QUAL §5](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [QCP §1](../assurance/qualification-campaign/1-select-the-qualification-scope-and-acceptance-claim.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

Page counts, schema checks, resource creation and test counts establish different things from effective infrastructure control and accepted residual risk.

## Decision recorded in the source

Qualify the actual service, versions and topology with applicable observations. Keep document quality, technical conformance, operational readiness and formal authorization distinct and attributable.

## Alternatives and limits recorded in the source

The first stack is qualified with applicable single-stack observations; cross-platform comparison and actual exit recovery establish separate additional claims. Two pre-qualified stacks are not a prerequisite to qualifying the first.

## Consequences

Blocked, not-run and unjustified not-applicable results cannot satisfy required observations. Historical source results remain historical and do not automatically apply to changed configurations.

## Engineering and implementation obligations

Link each applicable requirement assertion to its actual target, healthy control, observation, artifact, reviewer and separate operating decision.

## Requirement and code traceability

[AUTH-001](../assurance/requirements.md#AUTH-001) · [TEST-003](../assurance/requirements.md#TEST-003) · [EVID-003](../assurance/requirements.md#EVID-003) · [ACPT-001](../assurance/requirements.md#ACPT-001)

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/check_local.py](../../tools/check_local.py)
- [tools/verify_terraform.py](../../tools/verify_terraform.py)
- [scripts/verify_ansible.py](../../scripts/verify_ansible.py)
- [quality](../../quality)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Live platform evidence, selected controls, independent review and issued authorization remain outside this documentation migration.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

## Proposed clarification — First qualification, equivalent deployment and actual exit

Accept the first platform against applicable single-stack assertions without a circular second-platform prerequisite. Qualify the second platform independently; then separately measure image/data/service exit and its consistency, identity/key dependencies, rollback limits and exceptions before making that portability claim.

Source basis: [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [QUAL §5](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md). This clarification is not an accepted historical decision.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
