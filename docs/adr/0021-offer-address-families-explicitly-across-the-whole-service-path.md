# ADR-0021 — Offer address families explicitly across the whole service path

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [WD §11](../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

Testing IPv4 alone can leave an alternative protocol path uncontrolled. A stored AAAA record is not proof of routed IPv6 support.

## Decision recorded in the source

Explicitly offer IPv4-only, IPv6-only or dual-stack only when every required transport, gateway, boundary, service and recovery path supports that offer. Govern IPv6 local and transition behaviour even in an IPv4-only class.

## Alternatives and limits recorded in the source

The reference allows service-specific family choices; it does not require pretending an unsupported platform is dual-stack or inventing an IPv4 allocation for IPv6-only intent.

## Consequences

MTU and protocol control are path-specific. Required ICMPv6 and path-MTU behaviour must survive the selected policy. Encapsulation assumptions need actual packet-field accounting.

## Engineering and implementation obligations

Record enabled families, source validation, local control, effective MTU and positive/negative evidence per offered path and failure state.

## Requirement and code traceability

[IPV6-001](../assurance/requirements.md#IPV6-001) · [IPV6-002](../assurance/requirements.md#IPV6-002) · [IPV6-003](../assurance/requirements.md#IPV6-003)

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/route_audit.py](../../tools/route_audit.py)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

The native source and routed fixture remain IPv4-focused; offline IPv6 or loopback evidence does not satisfy native routed qualification.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
