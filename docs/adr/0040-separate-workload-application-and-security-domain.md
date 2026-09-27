# ADR-0040 — Separate workloads and applications from security domains

**Status:** Proposed<br>
**Decision class:** New product direction; organizational adoption pending<br>
**Date:** 2026-09-26<br>
**Accountable role:** Product/domain architecture and tenant security owners; named organizational acceptance is pending<br>
**Scope:** Canonical inventory, assessment, provisioning and migration model; no site realization is approved<br>
**Basis:** [ADR-0018](0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md), [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md), current `provisioner` WSD request and mobility models

## Context

A WSD establishes hosting isolation, policy and placement boundaries. It is not an inventory record for an arbitrary existing VM or a complete application topology. A single logical WSD image cannot represent multiple brownfield VMs, disks, NICs, external dependencies and independent data lifecycles. A move can affect a subset of one WSD or an application spanning several security domains.

## Decision

Introduce stable `Workload` and `ApplicationGroup` identities alongside `WorkloadSecurityDomain`:

| Object | Identity and ownership |
| --- | --- |
| Workload | Stable product ID, organization/tenant owner, observed native bindings, guest and device specification, lifecycle and selected WSD membership |
| ApplicationGroup | Explicit workload and dataset membership, dependency/consistency groups, startup order, objectives and application-owner acceptance |
| WSD | Existing isolation, policy, environment and placement boundary; may host several workloads and outlive an individual move |
| NativeBinding | Exact platform endpoint and native resource ID, observation version/time and binding role; source and destination can coexist during migration |
| Dataset | Exact source volume/path/backup lineage and destination mapping, owner, consistency point, integrity and retention obligations |

Names, addresses and display labels are mutable and cannot stand in for native identity. Keep desired, observed and last-accepted state separate; represent unknown or unavailable facts explicitly. A read-only discovery record becomes managed only after owner review, no-change import planning, authenticated authority and native confirmation. A WSD move and a workload move remain independent operations that may be composed.

The plan may select a single VM, an application group, a subset of a WSD or a wave. Every plan lists the precise workload/dataset set and source/destination bindings; it cannot infer that every member of a WSD should move.

## Alternatives considered

- Extending the WSD request with an optional flat VM list would conflate security-domain lifecycle and workload identity while leaving application dependencies unclear.
- Treating native VM names as primary keys would break across rename, clone and migration.

These are product modeling choices. [ADR-0018](0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md) continues to govern tenant and domain realization.

## Consequences and delivery obligations

- Model multi-VM, multi-disk and multi-NIC cases, device and guest incompatibilities, source observation completeness, and application dependency confidence.
- Assess security and policy equivalence against the selected destination WSD; a matching WSD label is insufficient.
- Bind data transfer and cutover to dataset/consistency-group identities; require one accepted production writer per consistency group.
- Implement explicit source and destination membership transitions and history, including same-platform site moves and post-cutover retained source records.
- Require tenant and application ownership review before brownfield adoption, migration or retirement.

## Acceptance

Canonical schemas, admission checks and behavioral tests must cover single VM, multi-VM application, partial WSD and incomplete discovery cases. Native qualification and operational adoption remain separate.

[Decision register](README.md)
