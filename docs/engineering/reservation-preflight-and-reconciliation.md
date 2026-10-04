# Reservation preflight and reconciliation evidence

**Purpose:** define the external reservation handoff required by the architecture without making this repository the live reservation service.

RA §23 requires Step 2 reservations to have an owner and expiry. PROV §4 requires compute/data demand, domain attachments and actual address allocations to be reserved under owner identities, with unused reservations released or a clearly owned pending allocation retained. PROV §5 requires ambiguous outcomes to stop and be discovered rather than guessed. API-003, AUTO-002/003, STATE-003 and EVID-002 add immutable IDs, idempotency, optimistic/current-generation checks, stable identity, evidence binding and reconciliation.

## Authority boundary

The authoritative reservation system remains external. `sources/capabilities/reservation_record_index.json` contains only exported/reviewed reservation evidence and is intentionally empty in the repository baseline. CI never creates, extends, consumes or releases a reservation.

The record-state vocabulary `HELD`, `CONSUMED`, `RELEASED`, `EXPIRED` and `UNCERTAIN` is an implementation record model for this repository contract. It is not a requirement that an external product expose those exact state names.

## Stable reservation identity

A reservation intent binds an immutable `reservation_id`, stable `operation_id`, generation, WSD/request identity, exact eligible envelope ID, the current commissioned-envelope SHA-256, exact capacity-request content digest, owner roles, resource dimensions/units/quantities, dependency operation IDs and expiry. The envelope digest is derived from the validated current site/service inventory; callers do not invent it.

The preflight recomputes the capacity request and current commissioned envelope and requires the reservation resource set to match exactly. The normalized spec hash includes the envelope SHA-256. A changed quantity, unit, envelope ID, envelope contents or generation under the same operation identity is therefore a conflict rather than an idempotent retry.

## Envelope-drift boundary

The exported reservation record also retains the commissioned-envelope SHA-256. Reusing the same `envelope_id` is insufficient: an existing HELD/CONSUMED record is idempotent only when the current envelope digest still matches the digest incorporated into the original immutable reservation spec.

If a capacity measurement, qualification binding, profile, failure model or other envelope content changes under the same ID, the recomputed spec differs and the preflight returns a conflict requiring authoritative reconciliation. It does not reinterpret the old reservation as covering the new envelope.

## Retry and uncertain-outcome rules

- Same operation + same reservation + same spec + confirmed held record: reuse the existing reservation; do not create another.
- Same operation or reservation identity with a changed spec: stop as a conflict.
- `UNCERTAIN` reservation or dependency handoff: discover the authoritative outcome before retry.
- `CONSUMED`: do not recreate; continue only under the owning workflow.
- `RELEASED` or `EXPIRED`: do not revive the terminal reservation; a new approved attempt needs a new operation identity.
- A `HELD` export observed after its expiry is inconsistent until the authoritative owner reconciles it; expiry is not silently treated as free reusable capacity.

## Dependency handoffs

External reservations such as IPAM remain under their own owners. The repository intent carries only the dependency kind, owner role and stable operation ID. Exported evidence may carry an authoritative reservation reference once the external owner confirms it. No IP address, prefix or DNS value is guessed by this layer.

## Current expected result

The active site/service envelope inventory and reservation evidence index are empty, so the repository example remains:

```sh
python -m provisioner.allocations.reservation_preflight examples/reservation_intent.json.example --as-of 2026-09-18T18:00:00Z --expected-status HOLD_ENVELOPE_NOT_CURRENTLY_ELIGIBLE
```

All mutation and activation flags remain false. A future ready result means only that the exact immutable spec may be submitted to the authoritative reservation owner under its accepted interface.

[Provisioning sequence](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [Safe activation](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [Concurrency and failure](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [Site/service capacity eligibility](site-service-capacity-eligibility.md)

## Installed record reader

The existing exported-record implementation is now package-owned at
`provisioner.allocations.reservation_evidence`; its former script is retired without
an alias. [The runtime contract](reservation-evidence-runtime.md) describes bounded
file input, exact artifact references, installed execution and unchanged evidence
semantics. This does not implement the external reservation authority or transactional
reserve/renew/confirm/release workflow.
