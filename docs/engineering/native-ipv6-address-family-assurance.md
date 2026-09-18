# Native IPv6 and address-family assurance

**Purpose:** close the I08 evidence-model gap between the repository's routed IPv6 laboratory and a real offered IPv6/dual-stack service.

The routed IPv6 laboratory is meaningful packet evidence, but it is intentionally synthetic. It does not establish that an installed Nutanix, VMware/NSX or OpenStack stack, its selected security edge, shared services, overlay MTU, management boundaries and recovery procedures support the same family safely in production.

## Source obligations

- IPV6-001 requires equivalent security semantics across IPv4 and IPv6 unless an explicit approved exception exists.
- IPV6-002 requires IPv6 negative-path testing before certifying dual-stack service.
- IPV6-003 requires every offered address-family mode to define local protocol controls, ICMPv6/PMTU treatment, transition restrictions and complete service/recovery dependencies; unsupported combinations must be rejected.
- ADR-0021 keeps the address-family offer end-to-end rather than a per-subnet toggle.
- NET §§3–5 require path, reply, negative, MTU and failure evidence.
- The existing routed IPv6 work package records Linux namespace evidence only and explicitly leaves native platform/service qualification open.

## Active assurance index

The active index is `sources/capabilities/address_family_assurance_index.json` and is intentionally empty.

A future record binds one `qualification_id` to:

- platform family;
- offered mode (`IPV6_ONLY` or `DUAL_STACK`);
- exact ordered family set;
- service class;
- platform profile and native qualification reference;
- one or more accepted security-edge assurance references;
- accountable owner and review cadence.

No actual IPv6 address or prefix is stored in this index. Address allocation remains under the authoritative IPAM owner.

## Native path evidence

Current native-path evidence requires:

- routing and return-path realization;
- same-host/distributed enforcement;
- source/neighbor controls;
- actual address-assignment mode;
- local-protocol controls;
- transition-mechanism restrictions;
- management-path exclusion.

This prevents a platform from being called IPv6-ready because an interface can hold an IPv6 address while policy, same-host paths, ND/RA behavior or management exposure remain unqualified.

## Security equivalence

The record requires an IPv4 baseline plus current evidence for:

- policy equivalence;
- negative-path behavior;
- inspection equivalence;
- attributable logging;
- fail-secure behavior.

For `DUAL_STACK`, this is the direct evidence behind IPV6-001/002. For `IPV6_ONLY`, the IPv4 baseline remains the reference security outcome so that protocol-family differences do not silently weaken the service contract.

## Shared-service dependencies

The offered family is not complete until its required shared-service paths are evidenced:

- DNS AAAA;
- DNS UDP/TCP including fallback;
- time service;
- trust/identity;
- telemetry;
- image/repository access;
- protection/recovery;
- origin-specific service reply routing.

An AAAA answer or loopback TLS exchange alone does not satisfy this dependency set.

## PMTU and packet behavior

Current PMTU evidence requires:

- effective workload MTU;
- actual encapsulation budget;
- ICMPv6 error policy;
- Packet Too Big behavior;
- healthy small/large transfer controls;
- fragment/extension-header policy.

The local 1280-byte Linux PTB campaign is useful supporting evidence but does not establish the native overlay, encryption or service-insertion budget.

## Failure and recovery evidence

Current failure evidence covers:

- route withdrawal;
- security-edge failure;
- origin-specific service-reply loss;
- address/DAD recovery;
- proof that IPv6 failure does not silently fall back to IPv4;
- survivor capacity.

Family qualification therefore includes recovery behavior rather than only healthy-path connectivity.

## Operations evidence

The record also requires current monitoring, runbook, controlled recovery/re-exposure and operational-acceptance references for the offered family.

## States

Supported states are:

- `CURRENT_QUALIFIED` — scope, packet/security/PMTU/failure and dependency/operations evidence are current and no OPEN gaps remain;
- `REVIEW_DUE` — scope or gap review expired;
- `PACKET_TEST_DUE` — native path, security-equivalence, PMTU or failure evidence is stale;
- `DEPENDENCY_DUE` — packet evidence remains current but shared-service or operations evidence is stale;
- `GAPS_OPEN` — current evidence exists but unresolved address-family gaps remain;
- `UNCERTAIN` — authoritative family/path/dependency state requires reconciliation.

## Readiness preflight

`scripts/check_address_family_readiness.py` compares the requested platform, offered mode, exact family set, service class and platform profile with the active assurance record.

A successful result is `ADDRESS_FAMILY_CURRENT_NO_NETWORK_MUTATION_AUTHORIZED`.

It does **not** authorize:

- address allocation;
- enabling IPv6;
- route changes;
- firewall/policy changes;
- shared-service changes;
- infrastructure apply;
- production activation.

Current repository state remains held because no installed native platform/service has supplied the complete evidence set:

```sh
python scripts/check_address_family_readiness.py examples/address_family_readiness_intent.json.example --as-of 2026-09-18T22:45:00Z --expected-status HOLD_NO_CURRENT_ADDRESS_FAMILY_ASSURANCE
```

The existing routed IPv6 workflow remains a required regression and supporting laboratory signal, not production family qualification.

[Routed IPv6 engineering profile](routed-ipv6-qualification.md) · [Routed IPv6 lab procedure](../implementation/routed-ipv6-lab.md) · [IPV6 assertion allocation](../implementation/allocation/ipv6.md)
