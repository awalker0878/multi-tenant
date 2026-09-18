# ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table

**Status:** Proposed<br>
**Accountable role:** Platform engineering<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) · [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) · [PBS §4](../engineering/platform-build/4-vmware-nsx-commission-transport-compute-and-edge-roles.md) · [PBS §5](../engineering/platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Independent Tier-1 names do not prevent routing between their prefixes through a common unrestricted Tier-0. Distributed routing and Edge-hosted service routing have different packet paths.

## Decision

Use a domain Tier-1 with an isolated upstream context, such as a supported Tier-0 VRF, toward the security edge. Do not enable unrestricted native inter-VRF route leaking. Keep mandatory endpoint policy distinct from the ZIP function.

## Alternatives and source limitations

Another isolated upstream pattern is possible when qualified for the selected release. Native or distributed ZIP alternatives require complete functional equivalence, not just a Tier-1 object.

## Consequences

Shared Edge or parent-gateway resources are shared capacity/failure dependencies, not shared authorization. A conceptual Edge drawing does not prove every relevant packet receives stateful inspection.

## Engineering and implementation obligations

Record advertisements, connected/distributed routes, gateway service components, uplinks, return paths, group hierarchy and exact vSphere/NSX/provider support.

## Requirement and code traceability

[NSX-001](../assurance/requirements.md#NSX-001) · [NSX-002](../assurance/requirements.md#NSX-002) · [NSX-003](../assurance/requirements.md#NSX-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Tier-0/VRF/Edge/interface construction and effective per-node enforcement are not provided or qualified by the current static-route and readback scopes.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
