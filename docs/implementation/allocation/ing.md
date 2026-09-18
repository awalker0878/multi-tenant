# ING — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## ING-001

A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network.


### ING-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network.

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-006, CT-025

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## ING-002

Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state.


### ING-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state.

**Owner / location:** Service owner / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-006, CT-063

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
