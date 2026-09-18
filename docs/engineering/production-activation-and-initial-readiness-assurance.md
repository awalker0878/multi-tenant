# Production activation and initial-readiness assurance

**Purpose:** close I10 without turning this repository into a production activation engine or authorizing authority.

A successful infrastructure build does not authorize production use. The source model requires G0/G1/G2 evidence, current operating authority, applicable initial G4 operating/recovery readiness, and an explicitly reversible G3 exposure change. Live production checks then confirm the actual entry/reply and dependency paths; failed or unknown checks require controlled withdrawal while preserving owned data and evidence.

## Source obligations

- IK §7 requires production activation prerequisites beyond successful infrastructure creation.
- PROV §4 requires accepted platform/service capability, current workload checks, operational/recovery readiness and valid authority before G3.
- ADR-0015 requires deny-before-connect, pre/post activation verification and reversible withdrawal.
- ADR-0036 requires applicable initial G4 readiness before G3 activation.
- IT §7 treats activation as an attributable decision record rather than a calculated approval.
- QUAL §7 keeps tenant service activation authority distinct from execution and formal system authorization.

## Active assurance index

The active index is `sources/capabilities/production_activation_assurance_index.json` and is intentionally empty.

A future activation record binds:

- activation ID;
- exact site, service class and platform profile;
- exact workload scope and exposure profile;
- accountable service owner;
- review cadence.

## Prerequisite evidence

The prerequisite block records current evidence references for:

- G0 reference adoption;
- G1 site/service design;
- G2 platform/service qualification;
- current capacity;
- held reservation;
- address/IPAM/DNS readiness;
- security-edge assurance;
- control inheritance;
- backup/restore assurance;
- native reconciliation;
- address-family readiness;
- operational handover.

These are references to accepted/current records. The activation checker does not recreate or silently replace their respective authorities.

## Initial G4 readiness

Before a record can become `READY_FOR_CONTROLLED_ACTIVATION`, it also requires current evidence for:

- recovery readiness;
- monitoring/alerting;
- named owner/on-call responsibility;
- credential/custody readiness;
- incident containment/release capability.

These are initial prerequisites for the offered service promise. A future recovery drill is not a substitute for initial readiness.

## Operating authority and reversible G3 change

The activation block records:

- operating-authority status and reference;
- attributable activation decision;
- authority validity;
- change record;
- exact exposure scope;
- reversible change plan;
- pre-activation verification.

`READY_FOR_CONTROLLED_ACTIVATION` requires current `APPROVED` or `CONDITIONAL` authority, but that state still grants **no activation authority to this repository**.

Before activation, `activation_receipt_ref` and `activated_at` must be absent.

## Post-activation evidence

After an externally authorized activation, the record may carry the activation receipt/time and must verify:

- actual live entry/reply behavior;
- affected dependency paths such as DNS/NAT/load balancing/routing where applicable;
- monitoring/telemetry witness.

A passing, current observation permits the evidence state `CURRENT_ACTIVATED`.

A missing or stale live observation results in `POST_ACTIVATION_DUE`.

A failed or unknown live observation results in `WITHDRAWAL_REQUIRED`; it can never be promoted to `CURRENT_ACTIVATED`.

## Withdrawal readiness

The withdrawal block records the data-preserving withdrawal plan, tested procedure, owned-data preservation evidence and session-withdrawal behavior.

Before activation, withdrawal must be `TESTED_READY`. If live verification fails or becomes unknown, the activation record becomes `WITHDRAWAL_REQUIRED` and the designated external authority executes the withdrawal. CI does not remove exposure or terminate sessions.

## States

Supported states are:

- `READY_FOR_CONTROLLED_ACTIVATION` — prerequisites, initial G4, authority and withdrawal readiness are current; no activation receipt exists;
- `CURRENT_ACTIVATED` — activation receipt exists and current post-activation verification passed;
- `REVIEW_DUE` — scope or gap review expired;
- `INITIAL_READINESS_DUE` — prerequisites, initial G4, withdrawal readiness or authority validity expired;
- `POST_ACTIVATION_DUE` — activation occurred but live verification is missing or stale without a known failure;
- `WITHDRAWAL_REQUIRED` — live verification failed or is unknown and controlled withdrawal is required;
- `GAPS_OPEN` — current pre-activation evidence exists but residual gaps remain open;
- `UNCERTAIN` — authoritative activation state cannot yet be reconciled.

## Readiness preflight

`scripts/check_production_activation_readiness.py` checks one exact activation/site/service/platform/workload/exposure scope.

A pre-activation success is `PRODUCTION_ACTIVATION_PREREQUISITES_CURRENT_NO_ACTIVATION_AUTHORIZED`.

An already activated/current record returns `PRODUCTION_SERVICE_ALREADY_ACTIVATED_CURRENT_NO_CHANGE_AUTHORIZED`.

Neither status authorizes:

- quarantine release;
- exposure change;
- production activation;
- session withdrawal;
- infrastructure apply;
- deletion.

Current repository state remains held because no genuine activation authority or target-specific production evidence has been supplied:

```sh
python scripts/check_production_activation_readiness.py examples/production_activation_readiness_intent.json.example --as-of 2026-09-18T22:05:00Z --expected-status HOLD_NO_CURRENT_PRODUCTION_ACTIVATION_ASSURANCE
```

Actual activation, failed-path withdrawal and any later exposure change remain external accountable production changes.

[IK §7 — Controlled production activation](../implementation/delivery-guide/7-tenant-provisioning-and-controlled-production-activation.md) · [PROV §4 — Safe activation](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [IT §7 — Gate decision](../templates/implementation-mop/7-gate-decision-and-production-activation.md)
