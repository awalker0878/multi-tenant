# Origin-specific shared-service reply assurance

**Purpose:** close I05 without turning this repository into a router, service controller, entitlement authority or production network authority.

A shared service is not safely integrated merely because a tenant can reach it. The service reply must return through the initiating tenant/domain's accepted security context, while alternate connected, summary, NAT/PBR, interface or default paths remain absent or constrained. The same service endpoint must not become tenant transit or administrative reachability.

## Source obligations

- SVC-001 prohibits broad routing to a shared-services supernet merely because one service is consumed.
- SVC-002 prefers zone-aligned endpoints where useful to avoid unnecessary cross-zone trust transitions.
- SVC-003 requires direction, endpoint identity, authentication, allowed scope, availability, failure behavior, management separation and binding revocation/lifecycle.
- EDGE-002 prohibits a shared attachment unless connected/neighbor/gateway/NAT/PBR paths preserve isolation and ZIP enforcement in normal and failure states.
- RTE-004 requires connected, recursive, summary, NAT/PBR and enabled-family forwarding to be compared with the approved graph before exposure.
- ADR-0035 requires shared-service replies to select the originating security context rather than an unrelated tenant/default route.
- QCP §3 requires service-side and edge observations, healthy controls, alternative-path review and missing-route/failure tests.

## Active assurance index

The active index is `sources/capabilities/service_reply_assurance_index.json` and is intentionally empty.

A future record binds one stable `reply_id` to:

- site and service class;
- exact service binding;
- originating security context;
- service endpoint;
- one address family (`IPV4` or `IPV6`);
- accountable owner and review cadence.

Dual-stack service offerings therefore require independently current family records rather than a generic `dual-stack=true` label.

## Service binding evidence

Current binding evidence requires:

- service profile;
- endpoint identity;
- authentication;
- tenant/resource entitlement;
- allowed operation;
- management separation;
- binding-expiry rule;
- revocation test.

A permitted route is not service entitlement, and service consumption is not administrative access.

## Forward/reply and alternative-path evidence

Current routing evidence requires:

- forward path;
- reply path;
- origin-specific return route;
- return-route owner;
- accepted security-edge assurance;
- effective native forwarding;
- source validation;
- connected-route review;
- summary-route review;
- NAT/PBR review;
- alternate-interface review;
- no-service-transit evidence.

Seeing one permitted flow on the expected edge is insufficient because another connected, imported, summary or policy path may still exist.

## Failure evidence

Current failure evidence requires:

- healthy service control;
- missing origin-specific reply-route test;
- unavailable-next-hop test;
- service-edge failure test;
- proof that another tenant/default route is not borrowed;
- unsolicited reverse-initiation denial;
- exact recovery test.

The required failure behavior is fail closed for the affected origin context while unrelated accepted service bindings remain independently evaluated.

## Operating evidence

The record also carries current service availability, telemetry, service-loss behavior, surviving capacity and service-version/lifecycle evidence.

Binding expiry or service-version retirement must therefore be reflected in the service-binding state rather than leaving an enduring route/permission.

## States

Supported states are:

- `CURRENT_QUALIFIED` — binding, path, failure and operating evidence are current with no OPEN gaps;
- `REVIEW_DUE` — scope or residual-gap review expired;
- `PATH_TEST_DUE` — forward/reply/alternative-path or failure evidence is stale;
- `BINDING_DUE` — path evidence remains current but binding or operations/lifecycle evidence is stale;
- `GAPS_OPEN` — current evidence exists with unresolved service-reply gaps;
- `UNCERTAIN` — authoritative service-binding or forwarding state requires reconciliation.

## Readiness preflight

`scripts/check_service_reply_readiness.py` evaluates one exact site/service-binding/origin/endpoint/address-family scope.

A successful result is `SERVICE_REPLY_CURRENT_NO_ROUTING_MUTATION_AUTHORIZED`.

It does **not** authorize route creation, service-binding changes, policy changes, binding revocation, service mutation, infrastructure apply or production activation.

Current repository state remains held because no actual shared-service implementation has supplied native route/binding evidence:

```sh
python scripts/check_service_reply_readiness.py examples/service_reply_readiness_intent.json.example --as-of 2026-09-19T12:30:00Z --expected-status HOLD_NO_CURRENT_SERVICE_REPLY_ASSURANCE
```

The existing routed IPv4/IPv6 fixtures remain supporting laboratory evidence only; actual service/gateway owners must populate this gate from the selected implementation.

[ADR-0035 — Origin-specific replies](../adr/0035-make-shared-service-replies-select-the-originating-security-context.md) · [NBD §2 — Forward/reply routes](network-boundaries/2-walk-f14-01-through-the-forward-and-reply-routes.md) · [QCP §3 — Observe paths and boundaries](../assurance/qualification-campaign/3-observe-network-paths-and-boundary-enforcement.md)
