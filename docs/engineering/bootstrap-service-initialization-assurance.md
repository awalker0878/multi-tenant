# Bootstrap service-initialization assurance

**Purpose:** close the remaining I06 layer between authoritative address/name records and a safely initialized platform or workload.

Authoritative IPAM allocation and DNS registration already have their own fail-closed handoff gates. This gate adds the minimum initialization dependencies that must be current before the new platform/workload can rely on steady-state automation or activation.

## Source obligations

- IPAM-004 requires idempotent allocation/DNS/DHCP lifecycle and forbids guessed allocations when IPAM is unavailable.
- SVC-001 through SVC-003 require explicitly scoped service consumption, endpoint identity/authentication, availability/failure behavior, management separation and binding revocation/lifecycle.
- IMG-001/002 require approved versioned images/baselines with provenance/support/hardening/vulnerability disposition plus runtime baseline verification.
- OBS-001 through OBS-003 require stable attribution, independent security-control logging, time integrity, buffering/loss indication and safe behavior during collection failure.
- AUTO-001 requires provisioning to stop rather than bypass missing admission/IPAM/route/policy authority.
- RA §21 and PROV §2 require a minimum trusted name/time/identity/certificate/key/artifact/recovery path without circular dependency on the platform being built.

## Active assurance index

The active index is `sources/capabilities/bootstrap_service_assurance_index.json` and is intentionally empty.

A future record binds one bootstrap profile to exact site/service/platform scope and an accountable owner/review cadence.

## Authoritative prerequisites

The prerequisite block references current authoritative evidence for:

- IPAM allocation;
- DNS registration;
- identity/cryptographic trust;
- address-family qualification;
- the required origin-specific shared-service reply bindings;
- independent recovery bootstrap.

These remain separate authorities. The bootstrap gate does not duplicate their data or mutate them.

## Initialization profile

Current initialization evidence defines:

- approved address-assignment mode;
- DHCP/metadata scope or controlled static equivalent;
- resolver profile;
- trusted time profile;
- approved artifact repository profile;
- trust bootstrap;
- required key access;
- exact initialization-network scope.

This explicitly prevents unrestricted provider/service-network reachability from being justified as 'bootstrap.'

## Image and runtime baseline

The artifact-baseline block requires:

- approved image/baseline;
- provenance/digest;
- support status;
- hardening;
- vulnerability disposition;
- runtime baseline verification after provisioning;
- retirement/rebuild policy.

Repository availability does not authorize arbitrary external downloads or unverified substitute images.

## Telemetry during initialization

Current bootstrap telemetry requires stable identity/attribution, required event coverage, time integrity, buffering/loss alerting and explicit collection-failure behavior.

Collection loss is an operating condition to surface, not a reason to disable logging obligations.

## Dependency failure behavior

The failure campaign records:

- IPAM unavailable without guessed allocation;
- resolver loss;
- time-source loss;
- artifact-repository loss;
- collector loss;
- proof that no unrestricted fallback path is opened.

Recovery uses only preapproved dependency paths.

## Transition to steady state

Temporary bootstrap dependencies remain controlled records. The transition block requires:

- temporary dependency register;
- temporary credential record;
- temporary route record;
- exception register;
- steady-state replacement;
- post-transfer verification;
- revocation/cleanup evidence;
- proof that bootstrap cleanup did not destroy the only required recovery dependency.

## States

Supported states are:

- `CURRENT_READY` — prerequisites, initialization, image/runtime baseline, telemetry, failure and transition evidence are current with no OPEN gaps;
- `REVIEW_DUE` — scope or residual-gap review expired;
- `DEPENDENCY_DUE` — authoritative prerequisite/initialization/image/telemetry evidence is stale;
- `FAILURE_TEST_DUE` — dependency evidence remains current but failure tests are stale;
- `TRANSITION_DUE` — dependency/failure evidence remains current but bootstrap-to-steady-state transition evidence is stale;
- `GAPS_OPEN` — current evidence exists with unresolved bootstrap gaps;
- `UNCERTAIN` — authoritative bootstrap state requires reconciliation.

## Readiness preflight

`scripts/check_bootstrap_service_readiness.py` evaluates one exact site/service/platform/bootstrap profile.

A successful result is `BOOTSTRAP_SERVICES_CURRENT_NO_INITIALIZATION_AUTHORIZED`.

It does **not** allocate addresses, register names, change DHCP/metadata, change time sources, issue credentials, fetch artifacts, change telemetry, retire temporary dependencies, apply infrastructure or activate production.

Current repository state remains held because no native bootstrap service set has supplied current evidence:

```sh
python scripts/check_bootstrap_service_readiness.py examples/bootstrap_service_readiness_intent.json.example --as-of 2026-09-19T12:30:00Z --expected-status HOLD_NO_CURRENT_BOOTSTRAP_SERVICE_ASSURANCE
```

[SVC §2 — Name, time, initialization and telemetry](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md) · [RA §21 — Day-0 bootstrap](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [PROV §2 — Commissioning without circular dependencies](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md)
