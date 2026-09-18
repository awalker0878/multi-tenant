# IPV6 — assertion allocation

[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)

These are source-grounded proposed allocations, not native compliance results.

## IPV6-001

Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists.


### IPV6-001.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-002, CT-031, CT-032

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IPV6-002

Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service.


### IPV6-002.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service.

**Owner / location:** Platform engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-002, CT-003, CT-031

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

## IPV6-003

Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies; unsupported family combinations SHALL be rejected.


### IPV6-003.A01

**Assertion:** Complete source obligation; all applicable clauses must be satisfied: Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies; unsupported family combinations SHALL be rejected.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Complete source obligation; all applicable clauses must be satisfied: Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies; unsupported family combinations SHALL be rejected.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-018, CT-031, CT-032

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IPV6-003.A02

**Assertion:** Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: Every offered address-family mode SHALL define local protocol controls, ICMPv6/PMTU treatment, transition-path restrictions and complete service/recovery dependencies

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-018, CT-031, CT-032

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending

### IPV6-003.A03

**Assertion:** unsupported family combinations SHALL be rejected.

**Owner / location:** Network engineering / Physical/overlay transport, site routing, OOB and actual address-family paths

**Disposition:** EXTERNAL_NATIVE_FABRIC_AND_SITE_ENGINEERING_REQUIRED. **Evidence class:** NATIVE_NOT_RUN; related local fixtures/engine checks are narrower evidence, not satisfaction

**Artifact or required operating record:** Accepted physical LLD, route/port/MTU/failure schedule and native configuration from the selected network owner — specifically: unsupported family combinations SHALL be rejected.

**Available related source:** [docs/current/TAD-infrastructure.md](../../current/TAD-infrastructure.md) · [docs/current/interface-agreements.md](../../current/interface-agreements.md) · [tools/route_audit.py](../../../tools/route_audit.py)

**Verification:** Inspect real route imports, port/overlay ownership, packet sizes and positive/negative paths for every offered family and declared failure. Baseline procedures: CT-018, CT-031, CT-032

**Remaining dependency:** Offline models and IPv6 loopback/AAAA checks are not a routed native IPv6 or physical-fabric implementation.

**Review state:** PROPOSED_ALLOCATION; actual applicability, named authority and evidence assignment pending
