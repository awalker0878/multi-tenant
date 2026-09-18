# ADR-0032 — Keep incident containment above routine reconciliation

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [OPS §2](../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Ordinary desired-state repair can reopen a connection deliberately blocked by an incident authority.

## Decision recorded in the source

Preserve scoped emergency containment until its explicit authorized release and reconciliation. Investigate security-significant drift without rewriting the historical authorization record.

## Alternatives and limits recorded in the source

Contain the narrowest effective workload, domain, service binding, exposure or capability while evaluating shared dependencies. Broad unrelated outages are not the default.

## Consequences

Current readiness and conformance can change while historical risk decisions remain immutable evidence. A generic emergency label is not permission to create unrestricted access.

## Engineering and implementation obligations

Record the incident authority, scope, precedence, required service dependencies, evidence, review/expiry and separate release decision.

## Requirement and code traceability

[DRIFT-001](../assurance/requirements.md#DRIFT-001) · [DRIFT-002](../assurance/requirements.md#DRIFT-002) · [DRIFT-003](../assurance/requirements.md#DRIFT-003) · [IR-001](../assurance/requirements.md#IR-001) · [IR-002](../assurance/requirements.md#IR-002)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

The local containment fixture and offline context review do not establish the actual incident process or production policy precedence.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
