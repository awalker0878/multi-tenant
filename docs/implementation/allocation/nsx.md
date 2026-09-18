# NSX — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## NSX-001

An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy.


### NSX-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy.

**Owner / location:** Platform engineering / Actual selected product/API/backend and mandatory provider-owned resource policy

**Disposition:** CANDIDATE_PARTIAL_VENDOR_REALIZATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Selected supported native version tuple, scoped privilege definitions and exact build artifacts; actual effective-state evidence — specifically: Complete source obligation; all applicable clauses must be satisfied: An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy.

**Available related source:** [terraform/modules/nsx-domain](../../../terraform/modules/nsx-domain) · [tools/nsx_observe.py](../../../tools/nsx_observe.py) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Exercise the applicable vendor CT/RA addendum using real delegated identities, native state and positive/negative/failure data paths. Baseline procedures: CT-019, CT-020, CT-066

**Remaining dependency:** Local API fixtures and mock plans do not qualify the installed hypervisor/backend or complete management/edge/Flow/DFW policies.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## NSX-002

Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload.


### NSX-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload.

**Owner / location:** Platform engineering / Actual selected product/API/backend and mandatory provider-owned resource policy

**Disposition:** CANDIDATE_PARTIAL_VENDOR_REALIZATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Selected supported native version tuple, scoped privilege definitions and exact build artifacts; actual effective-state evidence — specifically: Complete source obligation; all applicable clauses must be satisfied: Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload.

**Available related source:** [terraform/modules/nsx-domain](../../../terraform/modules/nsx-domain) · [tools/nsx_observe.py](../../../tools/nsx_observe.py) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Exercise the applicable vendor CT/RA addendum using real delegated identities, native state and positive/negative/failure data paths. Baseline procedures: CT-003, CT-007, CT-009

**Remaining dependency:** Local API fixtures and mock plans do not qualify the installed hypervisor/backend or complete management/edge/Flow/DFW policies.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## NSX-003

The NSX profile SHALL identify actual routing and enforcement components, global/project authority and policy precedence, and SHALL qualify their behavior on the selected product/provider tuple rather than equating a Tier-1 or project with a ZIP.


### NSX-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: The NSX profile SHALL identify actual routing and enforcement components, global/project authority and policy precedence, and SHALL qualify their behavior on the selected product/provider tuple rather than equating a Tier-1 or project with a ZIP.

**Owner / location:** Platform engineering / Actual selected product/API/backend and mandatory provider-owned resource policy

**Disposition:** CANDIDATE_PARTIAL_VENDOR_REALIZATION. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Selected supported native version tuple, scoped privilege definitions and exact build artifacts; actual effective-state evidence — specifically: Complete source obligation; all applicable clauses must be satisfied: The NSX profile SHALL identify actual routing and enforcement components, global/project authority and policy precedence, and SHALL qualify their behavior on the selected product/provider tuple rather than equating a Tier-1 or project with a ZIP.

**Available related source:** [terraform/modules/nsx-domain](../../../terraform/modules/nsx-domain) · [tools/nsx_observe.py](../../../tools/nsx_observe.py) · [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md)

**Verification:** Exercise the applicable vendor CT/RA addendum using real delegated identities, native state and positive/negative/failure data paths. Baseline procedures: CT-003, CT-015, CT-024, CT-080

**Remaining dependency:** Local API fixtures and mock plans do not qualify the installed hypervisor/backend or complete management/edge/Flow/DFW policies.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
