# ADR-0019 — Separate information impacts from service-level and recovery promises

**Status:** Proposed<br>
**Accountable role:** Security authority / Service owner / Continuity management<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [SDP §1](../solutions/design-method/1-define-the-offered-service-before-choosing-the-build.md) · [QUAL §4](../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A Protected B or Medium availability-impact label does not specify host topology, uptime, measured recovery time or a usable recovery point.

## Decision

Record confidentiality, integrity and availability impacts separately from control selection, isolation dimensions, resource classes, measured availability and recovery objectives.

## Alternatives and source limitations

The sources do not prescribe one numerical uptime or RTO/RPO for all workloads. Different offers require explicit measured parameters and exclusions.

## Consequences

Stronger service promises can require different dependencies and additional capacity, not merely a changed profile name. Backup scheduling alone does not establish an application-consistent RPO.

## Engineering and implementation obligations

Define each service indicator, measurement interval, tolerated failures, exclusions, recoverable consistency point and accepting service/data owner.

## Requirement and code traceability

[CAT-001](../assurance/requirements.md#CAT-001) · [REL-001](../assurance/requirements.md#REL-001) · [REC-002](../assurance/requirements.md#REC-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [docs/IMPLEMENTATION_SCOPE.md](../IMPLEMENTATION_SCOPE.md)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

No production SLO, RTO, RPO, retention interval or assurance approval is supplied by the reference figures.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
