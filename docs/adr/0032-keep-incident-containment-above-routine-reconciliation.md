# ADR-0032 — Keep incident containment above routine reconciliation

**Status:** Proposed<br>
**Accountable role:** Operations/SRE / Incident response<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [OPS §2](../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Ordinary desired-state repair can reopen a connection deliberately blocked by an incident authority.

## Decision

Preserve scoped emergency containment until its explicit authorized release and reconciliation. Investigate security-significant drift without rewriting the historical authorization record.

## Alternatives and source limitations

Contain the narrowest effective workload, domain, service binding, exposure or capability while evaluating shared dependencies. Broad unrelated outages are not the default.

## Consequences

Current readiness and conformance can change while historical risk decisions remain immutable evidence. A generic emergency label is not permission to create unrestricted access.

## Engineering and implementation obligations

Record the incident authority, scope, precedence, required service dependencies, evidence, review/expiry and separate release decision.

## Requirement and code traceability

[DRIFT-001](../assurance/requirements.md#DRIFT-001) · [DRIFT-002](../assurance/requirements.md#DRIFT-002) · [DRIFT-003](../assurance/requirements.md#DRIFT-003) · [IR-001](../assurance/requirements.md#IR-001) · [IR-002](../assurance/requirements.md#IR-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

The local containment fixture and offline context review do not establish the actual incident process or production policy precedence.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
