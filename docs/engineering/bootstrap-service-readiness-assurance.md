# Bootstrap service and steady-state transition assurance

**Purpose:** close the remaining I06 bootstrap-readiness gap without making this repository an IPAM, DNS, DHCP/metadata, identity, artifact, telemetry or platform bootstrap authority.

Authoritative IPAM allocation and DNS registration are already separate fail-closed handoffs. This gate composes those records with the minimum services and management dependencies required to initialize a site/platform/workload safely, then verifies transfer from temporary bootstrap dependencies to steady-state services without deleting the only recovery material.

## Source obligations

- RA §21 requires restricted console/OOB and initial trust before normal automation consumes native APIs.
- PROV §2 requires minimum trusted name/time, identity or emergency identity, certificate trust, key access, artifact access and recoverable configuration/state before the new cell is assumed available.
- SVC §2 requires scoped resolver, time, artifact, telemetry and related service profiles with explicit failure behavior.
- AUTO-001 requires provisioning to stop when required IPAM, route, admission or policy state is unavailable rather than inventing/bypassing it.
- MGT-005 requires independent management/OOB semantics and prevents tenant-facing APIs from exposing infrastructure administration.
- REC-001 requires independent bootstrap access and protected key/state/catalog recovery.
- QUAL-001 prevents bootstrap readiness from substituting for exact-tuple platform qualification.
- SVC-003 requires endpoint identity, authentication, allowed scope, availability/failure behavior, management separation and binding lifecycle.

## Active assurance index

The active index is `sources/capabilities/bootstrap_service_assurance_index.json` and is intentionally empty.

A future record binds one exact site/service/platform/bootstrap/address-family profile to five evidence groups.

## Authoritative address and name lifecycle

The authoritative lifecycle block requires references to:

- parent reservation;
- confirmed authoritative IPAM allocation;
- authoritative DNS registration;
- selected address-assignment method;
- DHCP/metadata profile where applicable;
- address/name reconciliation.

No literal IP address, prefix, FQDN, credential or secret is stored in this index.

## Minimum dependencies

Current minimum-dependency evidence requires:

- resolver profile;
- trusted time profile;
- identity/trust scope;
- certificate trust;
- required key access;
- approved artifact repository;
- telemetry profile;
- origin-specific service-reply assurance.

A reachable endpoint is insufficient if endpoint identity, entitlement, reply routing or failure behavior is not qualified.

## Restricted management and protected execution

Current evidence requires:

- restricted console/OOB;
- scoped initial privileged trust;
- restricted execution environment;
- artifact integrity;
- recoverable configuration/state;
- management isolation;
- dependency-cut review proving the recovery path survives the failure it is intended to recover from.

## Failure behavior

Bootstrap readiness includes explicit behavior for resolver, time, repository, telemetry and identity/trust loss. The record must prove there is no unrestricted external resolver, time source, download path, trust bypass or management shortcut used merely to finish provisioning.

## Transfer to steady state

Temporary bootstrap dependencies are recorded with:

- complete temporary dependency inventory;
- steady-state replacement mapping;
- temporary credential revocation;
- temporary route/grant cleanup;
- preservation of required emergency/recovery material;
- accepted handover.

Cleanup cannot destroy the only usable recovery path simply because steady-state services appear reachable.

## States

Supported states are:

- `CURRENT_QUALIFIED` — authoritative lifecycle, minimum dependencies, restricted management, failure behavior and handover evidence are current with no OPEN gaps;
- `REVIEW_DUE` — scope or residual-gap review expired;
- `DEPENDENCY_DUE` — authoritative IPAM/DNS/address or minimum service evidence is stale;
- `TRANSITION_DUE` — restricted-management, dependency-loss or steady-state transition evidence is stale;
- `GAPS_OPEN` — current evidence exists with unresolved bootstrap gaps;
- `UNCERTAIN` — authoritative bootstrap/transition state requires reconciliation.

## Readiness preflight

`scripts/check_bootstrap_service_readiness.py` evaluates one exact site/service/platform/bootstrap/address-family scope.

A successful result is `BOOTSTRAP_SERVICE_CURRENT_NO_BOOTSTRAP_MUTATION_AUTHORIZED`.

It does **not** authorize:

- address allocation;
- DNS registration;
- DHCP/metadata changes;
- credential issuance;
- shared-service binding changes;
- retirement of bootstrap dependencies;
- infrastructure apply;
- production activation.

Current repository state remains held because no actual bootstrap/service profile has supplied current target evidence:

```sh
python scripts/check_bootstrap_service_readiness.py examples/bootstrap_service_readiness_intent.json.example --as-of 2026-09-19T14:30:00Z --expected-status HOLD_NO_CURRENT_BOOTSTRAP_SERVICE_ASSURANCE
```

Actual bootstrap service mutations, temporary dependency retirement and steady-state handover remain external accountable operations.

[RA §21 — Day-0 bootstrap](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [PROV §2 — Day-0 and steady-state commissioning](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [SVC §2 — Name, time, initialization and telemetry](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md)
