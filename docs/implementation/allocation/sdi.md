# SDI — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## SDI-001

A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority.


### SDI-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority.

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-025, CT-035

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SDI-002

Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances.


### SDI-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances.

**Owner / location:** Platform engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-001, CT-002, CT-021

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SDI-003

Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation.


### SDI-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation.

**Owner / location:** Platform engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-018, CT-035

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SDI-004

Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization; membership and sharing changes SHALL be assessed as security-significant changes.


### SDI-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization; membership and sharing changes SHALL be assessed as security-significant changes.

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization; membership and sharing changes SHALL be assessed as security-significant changes.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-025, CT-035, CT-048

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SDI-004.A02

**Assertion:** Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-025, CT-035, CT-048

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SDI-004.A03

**Assertion:** membership and sharing changes SHALL be assessed as security-significant changes.

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: membership and sharing changes SHALL be assessed as security-significant changes.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-025, CT-035, CT-048

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
