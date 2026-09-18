# EVPN — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## EVPN-001

When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped; unapproved route imports SHALL be denied.


### EVPN-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped; unapproved route imports SHALL be denied.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped; unapproved route imports SHALL be denied.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-009, CT-033, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### EVPN-001.A02

**Assertion:** When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: When EVPN is used, RD/RT/VNI, gateway and multihoming policies SHALL be provider-owned, collision-checked and domain-scoped

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-009, CT-033, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### EVPN-001.A03

**Assertion:** unapproved route imports SHALL be denied.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: unapproved route imports SHALL be denied.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-009, CT-033, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## EVPN-002

Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior; vendor-specific MLAG interoperability SHALL NOT be assumed.


### EVPN-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior; vendor-specific MLAG interoperability SHALL NOT be assumed.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior; vendor-specific MLAG interoperability SHALL NOT be assumed.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-024, CT-032, CT-034

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### EVPN-002.A02

**Assertion:** Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Every multihoming and border interoperability profile SHALL be tested for split-brain, link/peer failure, MTU, route withdrawal and stateful-path behavior

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-024, CT-032, CT-034

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### EVPN-002.A03

**Assertion:** vendor-specific MLAG interoperability SHALL NOT be assumed.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: vendor-specific MLAG interoperability SHALL NOT be assumed.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-024, CT-032, CT-034

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
