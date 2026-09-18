# EDGE — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## EDGE-001

Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup; consumers SHALL NOT choose its native topology identifiers.


### EDGE-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup; consumers SHALL NOT choose its native topology identifiers.

**Owner / location:** Network engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup; consumers SHALL NOT choose its native topology identifiers.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-023, CT-024, CT-032, CT-071

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### EDGE-001.A02

**Assertion:** Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup

**Owner / location:** Network engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-023, CT-024, CT-032, CT-071

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### EDGE-001.A03

**Assertion:** consumers SHALL NOT choose its native topology identifiers.

**Owner / location:** Network engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: consumers SHALL NOT choose its native topology identifiers.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-023, CT-024, CT-032, CT-071

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## EDGE-002

A shared attachment SHALL be prohibited unless direct connected, neighbor, gateway and NAT/PBR paths preserve the required domain isolation and ZIP enforcement in normal and failure states.


### EDGE-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: A shared attachment SHALL be prohibited unless direct connected, neighbor, gateway and NAT/PBR paths preserve the required domain isolation and ZIP enforcement in normal and failure states.

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: A shared attachment SHALL be prohibited unless direct connected, neighbor, gateway and NAT/PBR paths preserve the required domain isolation and ZIP enforcement in normal and failure states.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-023, CT-024, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
