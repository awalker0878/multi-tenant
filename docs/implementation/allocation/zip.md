# ZIP — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## ZIP-001

All inter-zone network paths SHALL traverse the applicable ZIP/security edge.


### ZIP-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: All inter-zone network paths SHALL traverse the applicable ZIP/security edge.

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: All inter-zone network paths SHALL traverse the applicable ZIP/security edge.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-003, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## ZIP-002

A ZIP SHALL identify exactly two authorized adjacent endpoints, each an internal domain instance or approved external/management domain, and SHALL NOT create a general-purpose third-zone transit path.


### ZIP-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: A ZIP SHALL identify exactly two authorized adjacent endpoints, each an internal domain instance or approved external/management domain, and SHALL NOT create a general-purpose third-zone transit path.

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: A ZIP SHALL identify exactly two authorized adjacent endpoints, each an internal domain instance or approved external/management domain, and SHALL NOT create a general-purpose third-zone transit path.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-023, CT-025

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## ZIP-003

Default inter-zone policy SHALL be deny; allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.


### ZIP-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Default inter-zone policy SHALL be deny; allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Default inter-zone policy SHALL be deny; allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-007, CT-025, CT-066

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-003.A02

**Assertion:** Default inter-zone policy SHALL be deny

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Default inter-zone policy SHALL be deny

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-007, CT-025, CT-066

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-003.A03

**Assertion:** allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-007, CT-025, CT-066

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## ZIP-004

ZIP management traffic SHALL be segregated from operational traffic.


### ZIP-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: ZIP management traffic SHALL be segregated from operational traffic.

**Owner / location:** Security-edge operations / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: ZIP management traffic SHALL be segregated from operational traffic.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-004, CT-026

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## ZIP-005

Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services; shared virtualization SHALL only be used where the applicable assurance analysis supports it.


### ZIP-005.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services; shared virtualization SHALL only be used where the applicable assurance analysis supports it.

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services; shared virtualization SHALL only be used where the applicable assurance analysis supports it.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-026, CT-035, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-005.A02

**Assertion:** Separate data-path security service

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Separate data-path security service

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-026, CT-035, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-005.A03

**Assertion:** Separate management-path security service

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Separate management-path security service

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-026, CT-035, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-005.A04

**Assertion:** Shared virtualization is covered by actual assurance analysis

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Shared virtualization is covered by actual assurance analysis

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-026, CT-035, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## ZIP-006

Each ZIP SHALL record its two zone authorities, joint approval, required security functions, management authority, heightened posture, session-revocation behavior and current evidence.


### ZIP-006.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Each ZIP SHALL record its two zone authorities, joint approval, required security functions, management authority, heightened posture, session-revocation behavior and current evidence.

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: Each ZIP SHALL record its two zone authorities, joint approval, required security functions, management authority, heightened posture, session-revocation behavior and current evidence.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-006.A02

**Assertion:** Exactly the adjacent zone authorities

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Exactly the adjacent zone authorities

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-006.A03

**Assertion:** Joint approval

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Joint approval

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-006.A04

**Assertion:** Required security functions

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Required security functions

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-006.A05

**Assertion:** Management authority

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Management authority

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-006.A06

**Assertion:** Heightened posture

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Heightened posture

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-006.A07

**Assertion:** Existing-session withdrawal behaviour

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Existing-session withdrawal behaviour

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-006.A08

**Assertion:** Current attributable evidence

**Owner / location:** Security authority / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Current attributable evidence

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-067, CT-077, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## ZIP-007

A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge; any unsupported mandatory function SHALL make that realization ineligible.


### ZIP-007.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge; any unsupported mandatory function SHALL make that realization ineligible.

**Owner / location:** Platform engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: Complete source obligation; all applicable clauses must be satisfied: A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge; any unsupported mandatory function SHALL make that realization ineligible.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-003, CT-023, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-007.A02

**Assertion:** A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge

**Owner / location:** Platform engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-003, CT-023, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### ZIP-007.A03

**Assertion:** any unsupported mandatory function SHALL make that realization ineligible.

**Owner / location:** Platform engineering / Selected native domain/gateway/mandatory-policy scope plus independently owned EC/SE security edge

**Disposition:** CANDIDATE_PARTIAL_NATIVE_CONFIGURATION_WITH_EXTERNAL_EDGE_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Exact accepted native rule/route/attachment configuration and authority record for the assertion; packet/control-plane observations from both sides — specifically: any unsupported mandatory function SHALL make that realization ineligible.

**Available related source:** [terraform/modules](../../../terraform/modules) · [tools/route_audit.py](../../../tools/route_audit.py) · [docs/NATIVE_READBACK.md](../../NATIVE_READBACK.md)

**Verification:** Use the named CT procedure with healthy endpoints; inspect native connected/distributed alternatives, effective rules and forward/reply behaviour, including relevant failure. Baseline procedures: CT-003, CT-023, CT-080

**Remaining dependency:** A prepared VPC/Tier-1/router, exact static route or readback projection does not implement the entire ZIP, native tenant-role policy, isolation, inspection or HA.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
