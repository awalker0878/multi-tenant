# Operations drift, health and capacity review

`tools/operations_review.py` classifies scheduled operations evidence and routes
it to accountable owners. It compares exact configuration digests, reads declared
health, capacity and telemetry states, and preserves an active emergency override
instead of silently accepting the drifted value. It cannot repair drift, approve a
boundary, contain an edge or authorize production activation: a healthy review
still returns `ordinary_reconciliation_authorized: false`, `native_acceptance:
false` and `production_activation: false`.

## Private review input

The review is a private file with `format: hosting-operations-review/1` and
exactly these keys:

| Field | Contract |
| --- | --- |
| `source_commit` | 40-hex commit. `main` requires it to equal a clean checkout's `HASHES_MATCH` commit |
| `operation_id`, `generation` | Identifier and positive generation of this scheduled review |
| `scope` | `environment_key`, `site_key`, `platform`, `tenant_key`, `wsd_key`; platform is `nutanix`, `vmware` or `openstack` |
| `cadence_seconds` | Freshness window, 60 to 604800 seconds |
| `authorization_ref` | Accountable operating authority for this review |
| `routes` | Exactly the four alert routes below |
| `observations` | One or more unique observations |

| Route | Use |
| --- | --- |
| `operations` | Platform configuration, telemetry and general platform operations |
| `incident` | Security-significant drift and unknown or lost observations |
| `capacity` | Admission and capacity pressure |
| `service` | Declared service health |

Each route has `owner` and `route_ref`. A route is only a destination; selecting
it does not delegate containment authority.

## Observation kinds

| `kind` | Required fields | Permitted `state` |
| --- | --- | --- |
| `configuration` | Exact `expected_sha256` and `observed_sha256`; `state` must be null | Not applicable |
| `health` | No drift fields | `healthy`, `degraded`, `failed`, `unknown` |
| `capacity` | No drift fields | `within_envelope`, `warning`, `exhausted`, `unknown` |
| `telemetry` | No drift fields | `current`, `stale`, `unavailable`, `unknown` |

Every observation carries `id`, `owner_route`, `observed_at`, `evidence_ref`,
`security_relevant` and `containment_on_failure`. Non-configuration observations
cannot carry drift digests or an emergency override, so a health, capacity or
telemetry state can never be presented as an approved configuration value.
Capacity observations cannot set `containment_on_failure`: pressure is an
admission and operations hold, not automatic security containment. A
security-significant configuration observation must be containment eligible, so
the review cannot declare its own drift unrecoverable. An observation older than
`cadence_seconds`, or dated in the future, is not fresh.

## Classification

| Classification | Meaning |
| --- | --- |
| `MATCHED` | Expected and observed configuration digests are equal |
| `BENIGN_DRIFT` | Non-security configuration drift; routes an action, no containment |
| `SECURITY_CRITICAL` | Security-significant drift with no active override; containment eligible |
| `APPROVED_EMERGENCY` | Drift covered by an active override; preserved, never repaired |
| `HEALTHY`, `DEGRADED`, `FAILED` | Declared service health |
| `WITHIN_ENVELOPE`, `WARNING`, `EXHAUSTED` | Declared capacity state |
| `CURRENT`, `STALE`, `UNAVAILABLE` | Declared telemetry state |
| `UNKNOWN` | A stale, future-dated or explicitly unknown observation |

Severity is `critical` for `SECURITY_CRITICAL`, `FAILED`, `EXHAUSTED` and
`UNAVAILABLE`; `high` for `UNKNOWN`, `STALE` and `APPROVED_EMERGENCY`; `warning`
for the remaining non-healthy classes.

The overall status is the first matching case:

1. `OPERATIONS_HOLD_CONTAINMENT_REQUIRED` — any observation is containment
   eligible under its own `containment_on_failure` flag.
2. `OPERATIONS_HOLD_EMERGENCY_OVERRIDE_PRESERVED` — an active override is
   covering drift.
3. `OPERATIONS_ACTION_REQUIRED` — any other non-healthy observation.
4. `OPERATIONS_HEALTHY` — every observation is current and matches.

## Emergency override

An active override records `ref`, `expected_sha256`, `observed_sha256`,
`valid_from`, `valid_until`, `incident_ref` and `closure_ref`. Both digests must
equal the observation's own digests, so an override cannot be reused for a
different drift. An override is active only while `valid_from <= now <
valid_until` and `closure_ref` is null. A matched configuration cannot retain an
override, and an expired override does not become desired state: the drift is
classified as security-critical or unknown and can require containment. An
override that is present but inactive never downgrades severity.

## Alerts

Every non-healthy observation produces one alert with `observation_id`,
`classification`, `severity`, the owning route's `owner` and `route_ref`, and the
observation's `evidence_ref`. `containment_required` is set per alert and
aggregated into the result. The delivery runner writes these to `alerts.json`
with `format: hosting-operations-alerts/1` and the `review_sha256` of the review
they came from, so an alert set cannot be detached from the evidence that
produced it.

## Delivery integration

`operations_review` is a registered [delivery stage](delivery-runner.md) that
takes one private `review` file and writes `operations-review.json` and
`alerts.json`. Validation requires the review's `source_commit` and `scope` to
match the delivery plan, so a review from another plan cannot satisfy the stage.

`enforce()` raises `OperationsHold` for any status other than
`OPERATIONS_HEALTHY`. The hold carries `containment_required`, which the
[delivery containment guard](incident-containment.md) reads instead of assuming
withdrawal. A benign-drift or capacity hold therefore stops ordinary
reconciliation without withdrawing the owned edge boundary, while a
security-critical or unknown-observation hold withdraws it. A held review never
marks the stage successful and never advances the forward workflow.

After an interrupted run, recovery only reloads the existing artifacts. It
requires the recorded `review_sha256` to equal the digest of the private review
and the alert set to equal the recorded one exactly, and then re-raises the
original hold. An uncertain operations review is therefore never reclassified as
healthy by a retry.

## Command line

```sh
python tools/operations_review.py --review /private/operations-review.json \
  --output /private/operations-result.json
```

`main` requires the private review and a clean checkout whose commit equals
`source_commit`. It exits 0 only for `OPERATIONS_HEALTHY`; every other outcome,
including a rejected input, exits 2 with `HOLD_OPERATIONS_RECONCILIATION` and
`native_acceptance: false`.

## Limits

The review is a classification of supplied evidence. It performs no native read,
repair, boundary change or activation, and it does not qualify an observer, a
notification path or an operating authority. Observer coverage, alert delivery,
on-call acknowledgement, containment execution and production acceptance remain
native commissioning evidence under the [completion backlog](completion-backlog.md).