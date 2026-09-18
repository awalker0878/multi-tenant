# ADR-0011 — Default to site-local domains and routed recovery

**Status:** Proposed<br>
**Accountable role:** Platform engineering / Architecture authority / Recovery operations<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-09`<br>
**Source chapters:** [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) · [QUAL §2](../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Two site labels do not prove independence when power, storage, control or trust dependencies are shared. Layer-2 stretch extends failure and consistency responsibilities.

## Decision

Use site-local domain instances and explicit routed inter-site services for replication, recovery and declared access. Preserve the workload security purpose while recreating its site-specific realization.

## Alternatives and source limitations

Layer-2 stretch requires a demonstrated service need and separate partition, gateway-ownership, fencing and failback analysis.

## Consequences

Active multi-site service needs explicit data/application consistency supplied by its owner; VM restart alone does not provide it. Recovery is constrained by the target's own capacity and security eligibility.

## Engineering and implementation obligations

Record common dependencies, consistency points, failover authority, writer fencing, target validation and controlled service/DNS cutover.

## Requirement and code traceability

[SITE-001](../assurance/requirements.md#SITE-001) · [SITE-002](../assurance/requirements.md#SITE-002) · [SITE-003](../assurance/requirements.md#SITE-003) · [SITE-004](../assurance/requirements.md#SITE-004) · [REC-002](../assurance/requirements.md#REC-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [docs/COMMISSIONING.md](../COMMISSIONING.md)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Recovery sites, actual RTO/RPO, supported replication and witnessed partition/failback results remain open.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
