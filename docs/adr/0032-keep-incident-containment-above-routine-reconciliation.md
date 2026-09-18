# ADR-0032 — Keep incident containment above routine reconciliation

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [OPS §2](../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

The local containment fixture and offline context review do not establish the actual incident process or production policy precedence.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
