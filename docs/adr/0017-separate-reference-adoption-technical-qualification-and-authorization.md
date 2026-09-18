# ADR-0017 — Separate reference adoption, technical qualification and authorization

**Status:** Proposed<br>
**Accountable role:** Security authority / Assurance engineering / Delivery owner<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-15`<br>
**Source chapters:** [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [QUAL §5](../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md) · [QUAL §6](../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [QCP §1](../assurance/qualification-campaign/1-select-the-qualification-scope-and-acceptance-claim.md) · [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.
> **Editorial extension:** this record includes a separately identified audit-remediation proposal grounded in its linked sources; no original approval is inferred.


## Context

Page counts, schema checks, resource creation and test counts establish different things from effective infrastructure control and accepted residual risk.

## Decision

Qualify the actual service, versions and topology with applicable observations. Keep document quality, technical conformance, operational readiness and formal authorization distinct and attributable.

## Alternatives and source limitations

The first stack is qualified with applicable single-stack observations; cross-platform comparison and actual exit recovery establish separate additional claims. Two pre-qualified stacks are not a prerequisite to qualifying the first.

## Consequences

Blocked, not-run and unjustified not-applicable results cannot satisfy required observations. Historical source results remain historical and do not automatically apply to changed configurations.

Reference adoption, first-platform qualification, an additional platform meeting the same outcomes, and a representative usable-data/application exit rehearsal are separate claims. Local mocks and a successful disk conversion do not complete the latter.

## Engineering and implementation obligations

Link each applicable requirement assertion to its actual target, healthy control, observation, artifact, reviewer and separate operating decision. Validate these dependencies and record their owner, accepted configuration and failure/recovery observations before the affected service is offered.

## Requirement and code traceability

[AUTH-001](../assurance/requirements.md#AUTH-001) · [TEST-003](../assurance/requirements.md#TEST-003) · [EVID-003](../assurance/requirements.md#EVID-003) · [ACPT-001](../assurance/requirements.md#ACPT-001) · [DEL-001](../assurance/requirements.md#DEL-001) · [DEL-002](../assurance/requirements.md#DEL-002) · [PORT-001](../assurance/requirements.md#PORT-001) · [MIG-003](../assurance/requirements.md#MIG-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/check_local.py](../../tools/check_local.py)
- [tools/verify_terraform.py](../../tools/verify_terraform.py)
- [scripts/verify_ansible.py](../../scripts/verify_ansible.py)
- [quality](../../quality)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Live platform evidence, selected controls, independent review and issued authorization remain outside this documentation migration.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
