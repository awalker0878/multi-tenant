# ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) · [VND §4](../engineering/platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) · [PBS §4](../engineering/platform-build/4-vmware-nsx-commission-transport-compute-and-edge-roles.md) · [PBS §5](../engineering/platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Tier-0/VRF/Edge/interface construction and effective per-node enforcement are not provided or qualified by the current static-route and readback scopes.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
