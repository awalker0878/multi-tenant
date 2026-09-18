# Native IPv6 and address-family assurance

**Purpose:** close the remaining I08 evidence-model gap without promoting the routed Linux laboratory into native platform qualification.

The existing IPv6 laboratory already proves a bounded set of routed IPv6-only outcomes on disposable Linux namespaces: deny-first policy, exact routes, healthy negative controls, AAAA/DNS UDP/TCP fallback, routed TLS, Packet Too Big/PMTUD behavior, containment, route/link failure and explicit address/DAD recovery. A production service still needs evidence for the actual installed platform, security edge, shared services and operating scope.

## Source obligations

- IPV6-001 requires equivalent security outcomes for every offered address family.
- IPV6-002 requires family-specific negative testing before a dual-stack or IPv6-only offer is accepted.
- IPV6-003 requires explicit local-protocol, PMTU, transition, service and recovery dependencies.
- ZIP-001 and the ZIP assurance layer require inter-zone paths to remain behind the accepted security edge.
- RTE-002 requires controlled route authority and return-path behavior.
- SVC-001 requires explicit shared-service consumption paths rather than broad reachability.
- FAIL-001 requires accepted failure behavior rather than permissive fallback.
- TEST-003 requires target versions, healthy controls, expected outcomes and attributable evidence for every mandatory test execution.

## Active assurance index

The active index is `sources/capabilities/native_ipv6_assurance_index.json` and is intentionally empty.

A future record binds:

- site;
- service class;
- platform family and platform profile;
- security-edge profile;
- offered family mode (`IPV6_ONLY` or `DUAL_STACK`);
- accountable owner and review cadence.

## Platform and addressing applicability

Each record carries current evidence for the actual installed tuple/API/backend and the endpoint/management-exclusion profile used by the offered service.

Addressing evidence includes:

- addressing mode (`STATIC`, `SLAAC`, `DHCPV6` or `SLAAC_DHCPV6`);
- prefix scope and allocation authority;
- DAD;
- source-address validation;
- neighbour discovery;
- router-advertisement handling;
- DHCPv6 behavior;
- redirect policy;
- transition-mechanism policy.

Disabled/not-offered behaviors remain explicit evidence references rather than omitted assumptions.

## Local IPv6 protocol behavior

Current native evidence must cover:

- Neighbor Solicitation/Advertisement;
- ICMPv6 errors;
- Packet Too Big;
- MLD behavior where applicable;
- fragment policy;
- extension-header policy;
- hop-limit validation.

A product supporting IPv6 addressing is not sufficient if required local control traffic or error handling is blocked incorrectly.

## Routing and security parity

The record requires evidence for:

- route authority;
- forward/reply path;
- same-host/distributed paths;
- equivalent security outcomes across offered families;
- security-edge enforcement;
- management exclusion;
- origin-specific service replies;
- bypass-path review.

This prevents an IPv6 path from bypassing a security control that is effective only for IPv4.

## MTU and PMTU

The MTU/PMTU block records:

- packet/frame measurement convention;
- workload MTU;
- overlay/encapsulation budget;
- handoff MTU;
- PMTUD behavior;
- a negative Packet Too Big black-hole test.

The local Linux 1280-byte experiment is supporting evidence for the method. Native qualification must use the actual overlay, encryption and service-insertion path.

## Shared-service dependencies

The offered family is not accepted until the required service matrix is qualified over that family. Evidence includes:

- DNS AAAA plus UDP/TCP behavior;
- identity/TLS;
- time;
- telemetry;
- artifact/image repository;
- protection/recovery path.

A service may explicitly mark a dependency not offered in its controlled matrix, but it cannot silently inherit IPv4-only reachability.

## Failure and recovery

Current evidence covers:

- route withdrawal;
- edge/link failure;
- address/DAD recovery;
- surviving capacity;
- recovery service paths.

`IPV6_ONLY` additionally requires explicit proof that there is no hidden IPv4 fallback.

`DUAL_STACK` instead requires an independent current IPv4 campaign. IPv6 passing cannot make IPv4 healthy, and IPv4 passing cannot qualify IPv6.

## States

Supported states are:

- `CURRENT_QUALIFIED` — native campaign and review are current and no OPEN residual gaps remain;
- `REVIEW_DUE` — service/family scope review has expired;
- `QUALIFICATION_DUE` — previously passing native qualification is stale;
- `GAPS_OPEN` — current qualification exists but unresolved family-specific gaps remain;
- `UNCERTAIN` — authoritative family qualification is failed, incomplete or otherwise unresolved.

Only `CURRENT_QUALIFIED` represents a current address-family readiness prerequisite.

## Readiness preflight

`scripts/check_native_ipv6_readiness.py` evaluates one exact site/service/platform/security-edge/family-mode request.

A successful result is `NATIVE_IPV6_QUALIFICATION_CURRENT_NO_SERVICE_OFFER_AUTHORIZED`.

It does **not** authorize:

- offering IPv6 to consumers;
- address allocation or DHCPv6/SLAAC changes;
- route changes;
- security-policy changes;
- MTU changes;
- infrastructure apply;
- production activation.

Current repository state remains held because no actual selected native service has supplied this evidence:

```sh
python scripts/check_native_ipv6_readiness.py examples/native_ipv6_readiness_intent.json.example --as-of 2026-09-18T22:05:00Z --expected-status HOLD_NO_CURRENT_NATIVE_IPV6_ASSURANCE
```

The routed IPv6 laboratory remains a strong reusable qualification method, not a production acceptance record.

[Routed IPv6 qualification](routed-ipv6-qualification.md) · [Routed IPv6 execution](../implementation/routed-ipv6-lab.md) · [IPv6 assertion allocation](../implementation/allocation/ipv6.md)
