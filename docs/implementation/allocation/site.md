# SITE — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## SITE-001

Security Domain Instances SHOULD be site-local by default.


### SITE-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Security Domain Instances SHOULD be site-local by default.

**Owner / location:** Platform engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Security Domain Instances SHOULD be site-local by default.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-054, CT-055

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SITE-002

Layer-2 stretch across sites SHALL require a documented application/availability requirement and failure-domain analysis.


### SITE-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Layer-2 stretch across sites SHALL require a documented application/availability requirement and failure-domain analysis.

**Owner / location:** Architecture authority / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Layer-2 stretch across sites SHALL require a documented application/availability requirement and failure-domain analysis.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-054

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SITE-003

Recovery-site connectivity SHALL be pre-authorized and tested; emergency recovery SHALL NOT depend on ad hoc route leaking.


### SITE-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Recovery-site connectivity SHALL be pre-authorized and tested; emergency recovery SHALL NOT depend on ad hoc route leaking.

**Owner / location:** Recovery operations / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Recovery-site connectivity SHALL be pre-authorized and tested; emergency recovery SHALL NOT depend on ad hoc route leaking.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-052, CT-054

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SITE-003.A02

**Assertion:** Recovery-site connectivity SHALL be pre-authorized and tested

**Owner / location:** Recovery operations / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Recovery-site connectivity SHALL be pre-authorized and tested

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-052, CT-054

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SITE-003.A03

**Assertion:** emergency recovery SHALL NOT depend on ad hoc route leaking.

**Owner / location:** Recovery operations / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: emergency recovery SHALL NOT depend on ad hoc route leaking.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-052, CT-054

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## SITE-004

Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints; writer fencing and failback ownership SHALL be proven before production recovery is offered.


### SITE-004.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints; writer fencing and failback ownership SHALL be proven before production recovery is offered.

**Owner / location:** Recovery operations / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints; writer fencing and failback ownership SHALL be proven before production recovery is offered.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-035, CT-038, CT-054, CT-061

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SITE-004.A02

**Assertion:** Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints

**Owner / location:** Recovery operations / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Recovery placement SHALL preserve domain, co-residency, cryptographic, identity and location constraints

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-035, CT-038, CT-054, CT-061

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### SITE-004.A03

**Assertion:** writer fencing and failback ownership SHALL be proven before production recovery is offered.

**Owner / location:** Recovery operations / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: writer fencing and failback ownership SHALL be proven before production recovery is offered.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-035, CT-038, CT-054, CT-061

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
