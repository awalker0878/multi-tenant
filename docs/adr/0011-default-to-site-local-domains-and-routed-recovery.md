# ADR-0011 — Default to site-local domains and routed recovery

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-09`<br>
**Source chapters:** [RA §14](../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md) · [SVC §6](../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md) · [QUAL §2](../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [docs/COMMISSIONING.md](../COMMISSIONING.md)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Recovery sites, actual RTO/RPO, supported replication and witnessed partition/failback results remain open.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
