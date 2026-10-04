# Site, cell and service-class capacity eligibility

**Purpose:** implement the read-only evidence check immediately before an accountable reservation workflow. This is not a scheduler, reservation database, IPAM client or provisioning controller.

The architecture separates two placement levels: first select an eligible site, hosting cell and service class using qualified platform, security, service, location, recovery and capacity evidence; only then may the selected native platform scheduler place resources inside the approved pool. This package implements only the first level's engineering precheck.

## Source basis

The retained requirements are PLACE-001, SVCM-001, SVCM-002, CAP-001 and CAP-002. RA §4 and QUAL §3 require compute, storage, security-edge, attachment, address and shared-service capacity to be evaluated together under the accepted failure model. One failed bottleneck rejects the envelope.

## Active service envelope

The active machine-readable inventory is `sources/capabilities/site_service_capacity_index.json`. It is intentionally empty today.

A future CURRENT_COMMISSIONED record binds the site, cell, service class, exact platform tuple, assurance profiles, co-residency/compute/storage/network/security-edge/availability/recovery/location/key/backup profiles, failure model, current capacity measurements, owners and source evidence. Schema v2 also pins the exact qualification dossier SHA-256, approval decision reference, supporting campaign ID, selection ID, controlled site/cell references and campaign-scope reference used when the envelope was commissioned.

## Qualification immutability boundary

A commissioned envelope cannot rely only on a reusable qualification record ID. The validator recomputes the current approved dossier digest and requires it to equal the digest captured by the envelope. The approval decision must also be unchanged.

The envelope additionally names one current target-bound campaign scope that supports the dossier. That campaign must match the recorded campaign ID, selection ID, controlled site/cell references and campaign-scope reference, and it must contain the full native evidence set used by the approved qualification dossier. The campaign may contain additional evidence.

If the dossier changes under the same ID, its approval decision changes, or the supporting campaign/site/cell binding no longer matches, the envelope becomes invalid and must be recommissioned or explicitly re-approved. This prevents a capacity record from silently inheriting a later qualification state it was never measured or commissioned against.

## Capacity arithmetic

For every dimension:

```text
available = measured surviving capacity - operational reserve - existing commitment - unavailable capacity
```

Reserved and consumed are reporting observations, not quantities that are added together. Existing commitment is the authoritative already-admitted total and must be at least the larger of those observations. The procured, received, staged and commissioned values are retained as distinct lifecycle observations; this generic checker does not invent a cumulative arithmetic relationship between them. The admission calculation requires available >= 0 and keeps its measured-survivor/reserve/commitment/unavailable quantities in one declared unit.

These are consistency checks, not proof that a measurement is authentic.

## Request and quota boundary

A site-service demand provides the reviewed WSD reference, candidate platform families, optional site/cell/service-class restrictions, required assurance/profile references, and every demanded capacity dimension. Quota remaining is supplied by the approved quota authority; this precheck does not discover or mutate quota.

An envelope matches only when every requested dimension fits with the same unit and every mandatory profile matches. CPU or memory success cannot compensate for exhausted storage, edge sessions, attachment slots, address space or another required dimension.

## No reservation side effects

A matching result is `SITE_SERVICE_ENVELOPE_MATCH_RESERVATION_NOT_CREATED`. It does not select a winner or return a reservation ID. The fields may_select_site, may_reserve_capacity, may_allocate, may_allocate_address, may_apply and may_activate remain false.

The next implementation boundary is an accountable time-bounded reservation under the owners of the relevant resources. Authoritative IPAM allocation remains separate; no address may be guessed when IPAM is unavailable.

## Current repository state

Because the active native qualification index and site/service inventory are empty, the example remains held:

```sh
python -m provisioner.allocations.site_eligibility examples/site_service_capacity_request.json.example --expected-status HOLD_NO_ELIGIBLE_SITE_SERVICE_ENVELOPE
```

The example quantities and profile references are fixtures only, not site sizing, service commitments or approved thresholds.

[Hosting cells and failure boundaries](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [Capacity and service envelopes](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [Native PlatformProfile qualification](platform-native-qualification.md) · [Platform-family pre-placement](pre-placement-platform-eligibility.md)
