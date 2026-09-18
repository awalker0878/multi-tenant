# ADR-0011 — Default to site-local domains and routed recovery

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-09`<br>
**Source chapters:** [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) · [QUAL §2](../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Two site labels do not prove independence when power, storage, control or trust dependencies are shared. Layer-2 stretch extends failure and consistency responsibilities.

## Decision recorded in the source

Use site-local domain instances and explicit routed inter-site services for replication, recovery and declared access. Preserve the workload security purpose while recreating its site-specific realization.

## Alternatives and limits recorded in the source

Layer-2 stretch requires a demonstrated service need and separate partition, gateway-ownership, fencing and failback analysis.

## Consequences

Active multi-site service needs explicit data/application consistency supplied by its owner; VM restart alone does not provide it. Recovery is constrained by the target's own capacity and security eligibility.

## Engineering and implementation obligations

Record common dependencies, consistency points, failover authority, writer fencing, target validation and controlled service/DNS cutover.

## Requirement and code traceability

[SITE-001](../assurance/requirements.md#SITE-001) · [SITE-002](../assurance/requirements.md#SITE-002) · [SITE-003](../assurance/requirements.md#SITE-003) · [SITE-004](../assurance/requirements.md#SITE-004) · [REC-002](../assurance/requirements.md#REC-002)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [docs/COMMISSIONING.md](../COMMISSIONING.md)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Recovery sites, actual RTO/RPO, supported replication and witnessed partition/failback results remain open.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
