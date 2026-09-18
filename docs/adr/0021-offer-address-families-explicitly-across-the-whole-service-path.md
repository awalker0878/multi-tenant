# ADR-0021 — Offer address families explicitly across the whole service path

**Status:** Proposed<br>
**Accountable role:** Network engineering / Platform engineering<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [WD §11](../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Testing IPv4 alone can leave an alternative protocol path uncontrolled. A stored AAAA record is not proof of routed IPv6 support.

## Decision

Explicitly offer IPv4-only, IPv6-only or dual-stack only when every required transport, gateway, boundary, service and recovery path supports that offer. Govern IPv6 local and transition behaviour even in an IPv4-only class.

## Alternatives and source limitations

The reference allows service-specific family choices; it does not require pretending an unsupported platform is dual-stack or inventing an IPv4 allocation for IPv6-only intent.

## Consequences

MTU and protocol control are path-specific. Required ICMPv6 and path-MTU behaviour must survive the selected policy. Encapsulation assumptions need actual packet-field accounting.

## Engineering and implementation obligations

Record enabled families, source validation, local control, effective MTU and positive/negative evidence per offered path and failure state.

## Requirement and code traceability

[IPV6-001](../assurance/requirements.md#IPV6-001) · [IPV6-002](../assurance/requirements.md#IPV6-002) · [IPV6-003](../assurance/requirements.md#IPV6-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/route_audit.py](../../tools/route_audit.py)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

The native source and routed fixture remain IPv4-focused; offline IPv6 or loopback evidence does not satisfy native routed qualification.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
