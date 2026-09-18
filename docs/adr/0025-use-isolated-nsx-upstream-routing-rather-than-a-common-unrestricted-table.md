# ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) · [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) · [PBS §4](../engineering/platform-build/4-vmware-nsx-commission-transport-compute-and-edge-roles.md) · [PBS §5](../engineering/platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Independent Tier-1 names do not prevent routing between their prefixes through a common unrestricted Tier-0. Distributed routing and Edge-hosted service routing have different packet paths.

## Decision recorded in the source

Use a domain Tier-1 with an isolated upstream context, such as a supported Tier-0 VRF, toward the security edge. Do not enable unrestricted native inter-VRF route leaking. Keep mandatory endpoint policy distinct from the ZIP function.

## Alternatives and limits recorded in the source

Another isolated upstream pattern is possible when qualified for the selected release. Native or distributed ZIP alternatives require complete functional equivalence, not just a Tier-1 object.

## Consequences

Shared Edge or parent-gateway resources are shared capacity/failure dependencies, not shared authorization. A conceptual Edge drawing does not prove every relevant packet receives stateful inspection.

## Engineering and implementation obligations

Record advertisements, connected/distributed routes, gateway service components, uplinks, return paths, group hierarchy and exact vSphere/NSX/provider support.

## Requirement and code traceability

[NSX-001](../assurance/requirements.md#NSX-001) · [NSX-002](../assurance/requirements.md#NSX-002) · [NSX-003](../assurance/requirements.md#NSX-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Tier-0/VRF/Edge/interface construction and effective per-node enforcement are not provided or qualified by the current static-route and readback scopes.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
