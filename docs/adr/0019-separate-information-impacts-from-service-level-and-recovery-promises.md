# ADR-0019 — Separate information impacts from service-level and recovery promises

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [SDP §1](../solutions/design-method/1-define-the-offered-service-before-choosing-the-build.md) · [QUAL §4](../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

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

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [docs/IMPLEMENTATION_SCOPE.md](../IMPLEMENTATION_SCOPE.md)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

No production SLO, RTO, RPO, retention interval or assurance approval is supplied by the reference figures.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
