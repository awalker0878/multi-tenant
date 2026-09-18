# FAB — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## FAB-001

Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes; foundation growth and fabric-routed service classes SHALL use separately authorized workflows.


### FAB-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes; foundation growth and fabric-routed service classes SHALL use separately authorized workflows.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes; foundation growth and fabric-routed service classes SHALL use separately authorized workflows.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-071, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAB-001.A02

**Assertion:** Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Routine create, update and retirement of tenants/WSDs in a precommissioned overlay service class SHALL NOT require leaf/spine configuration changes

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-071, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### FAB-001.A03

**Assertion:** foundation growth and fabric-routed service classes SHALL use separately authorized workflows.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: foundation growth and fabric-routed service classes SHALL use separately authorized workflows.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-071, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## FAB-002

A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain.


### FAB-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-009, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## FAB-003

Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF.


### FAB-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF.

**Owner / location:** Architecture authority / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-025, CT-072

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## FAB-004

The fabric profile SHALL define addressing/routing authority, control-plane protection, MTU, fault convergence, management isolation, maintenance and measured scale before platform commissioning.


### FAB-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: The fabric profile SHALL define addressing/routing authority, control-plane protection, MTU, fault convergence, management isolation, maintenance and measured scale before platform commissioning.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: The fabric profile SHALL define addressing/routing authority, control-plane protection, MTU, fault convergence, management isolation, maintenance and measured scale before platform commissioning.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-026, CT-032, CT-033, CT-034

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
