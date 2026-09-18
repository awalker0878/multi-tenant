# EGR — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## EGR-001

Internet egress SHALL be deny-by-default and enabled only through an approved egress profile.


### EGR-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Internet egress SHALL be deny-by-default and enabled only through an approved egress profile.

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Internet egress SHALL be deny-by-default and enabled only through an approved egress profile.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-005, CT-064

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## EGR-002

Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible.


### EGR-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible.

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-010, CT-064

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
