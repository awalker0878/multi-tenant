# ADR-0017 — Separate reference adoption, technical qualification and authorization

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-15`<br>
**Source chapters:** [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [QUAL §5](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [QCP §1](../assurance/qualification-campaign/1-select-the-qualification-scope-and-acceptance-claim.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

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

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/check_local.py](../../tools/check_local.py)
- [tools/verify_terraform.py](../../tools/verify_terraform.py)
- [scripts/verify_ansible.py](../../scripts/verify_ansible.py)
- [quality](../../quality)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Live platform evidence, selected controls, independent review and issued authorization remain outside this documentation migration.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
