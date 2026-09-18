# ADR-0019 — Separate information impacts from service-level and recovery promises

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [SDP §1](../solutions/design-method/1-define-the-offered-service-before-choosing-the-build.md) · [QUAL §4](../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

A Protected B or Medium availability-impact label does not specify host topology, uptime, measured recovery time or a usable recovery point.

## Decision recorded in the source

Record confidentiality, integrity and availability impacts separately from control selection, isolation dimensions, resource classes, measured availability and recovery objectives.

## Alternatives and limits recorded in the source

The sources do not prescribe one numerical uptime or RTO/RPO for all workloads. Different offers require explicit measured parameters and exclusions.

## Consequences

Stronger service promises can require different dependencies and additional capacity, not merely a changed profile name. Backup scheduling alone does not establish an application-consistent RPO.

## Engineering and implementation obligations

Define each service indicator, measurement interval, tolerated failures, exclusions, recoverable consistency point and accepting service/data owner.

## Requirement and code traceability

[CAT-001](../assurance/requirements.md#CAT-001) · [REL-001](../assurance/requirements.md#REL-001) · [REC-002](../assurance/requirements.md#REC-002)

Related implementation areas are traceability targets, not proof of complete implementation:

- [docs/IMPLEMENTATION_SCOPE.md](../IMPLEMENTATION_SCOPE.md)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

No production SLO, RTO, RPO, retention interval or assurance approval is supplied by the reference figures.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
