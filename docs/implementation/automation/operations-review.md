# Operations drift, health and capacity review

`tools/operations_review.py` classifies scheduled operations evidence and routes
it to accountable owners. It compares exact configuration digests, reads declared
health, capacity and telemetry states, and preserves an active emergency override
instead of silently accepting the drifted value. It cannot repair drift, approve a
boundary, contain an edge or authorize production activation: a healthy review
still returns `ordinary_reconciliation_authorized: false`, `native_acceptance:
false` and `production_activation: false`.

`tools/operations_alerts.py` then binds the resulting alerts to accountable
acknowledgement, escalation and containment release, so a routed alert cannot be
closed by silence, by another owner or by a release that precedes the response.

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

`operations_alerts` is the companion [delivery stage](delivery-runner.md) that
binds the review's alerts to accountable acknowledgement. It takes the private
`review` and `result` documents plus an `acknowledgements` list, and an optional
`release` record, and writes `alert-accounting.json`.

## Alert acknowledgement and escalation

`tools/operations_alerts.py` turns each alert in a review result into an
accountability record. It never mutates a native resource and never asserts
acceptance; it decides only whether the alerts have been answered by the owner
that the review names.

An acknowledgement is `hosting-operations-acknowledgement/1` with keys
`format`, `review_sha256`, `observation_id`, `classification`, `owner`,
`acknowledged_by`, `acknowledged_at` and `response_ref`. Validation requires the
digest to equal the acknowledged result's `review_sha256`, the classification to
equal the alert's classification, the owner to equal the alert's accountable
route owner, and the observation to actually carry an alert. An alert therefore
cannot be closed against a different review, by a different route, or by naming
an observation that the review classified as healthy.

Escalation is measured against the review cadence. The deadline for an alert is
its observation's `observed_at` plus the review's `cadence_seconds`, and each
alert is classified as:

| State | Meaning |
|-------|---------|
| `PENDING` | No acknowledgement yet, before the cadence deadline |
| `ESCALATED` | No acknowledgement yet, at or after the cadence deadline |
| `ACKNOWLEDGED` | Acknowledged before the cadence deadline |
| `LATE` | Acknowledged, but only at or after the cadence deadline |

The accounting status is `ALERTS_NONE` when the review produced no alerts,
`ALERTS_ESCALATED` when any alert is `ESCALATED` or `LATE`, `ALERTS_PENDING`
when alerts remain unacknowledged inside their cadence, and `ALERTS_ACKNOWLEDGED`
when every alert was answered in time. Duplicate acknowledgements for one alert
and acknowledgements dated after the current review are rejected.

## Containment release

A release is `hosting-operations-containment-release/1` with keys `format`,
`review_sha256`, `observation_ids`, `authority_ref`, `released_at` and
`restoration_ref`. A release is authorized only when all of the following hold:

* the review requires containment for at least one alert;
* `observation_ids` names exactly the set of contained alerts, so a release
  cannot drop or smuggle an observation;
* every contained alert is `ACKNOWLEDGED` in time; and
* `released_at` is not earlier than the latest acknowledgement of a contained
  alert, so the release follows the accountable response rather than preceding it.

Otherwise the accounting records a blocking reason of `NO_CONTAINMENT_TO_RELEASE`,
`RELEASE_DOES_NOT_BIND_EXACT_CONTAINED_ALERTS`,
`CONTAINED_ALERT_NOT_ACKNOWLEDGED` or `RELEASE_PRECEDES_ACCOUNTABLE_RESPONSE`,
and `containment_release_authorized` stays false. A requested but unauthorized
release is a hold even when every alert was acknowledged.

`enforce()` raises `AlertHold`, in this order, for an escalated alert, for an
unacknowledged alert still inside its cadence, and for an unauthorized release.
`AlertHold` sets `containment_required` to `false` deliberately: a missing
acknowledgement is an accountability failure, not evidence that the owned edge
boundary is exposed, so it never withdraws containment through the
[delivery containment guard](incident-containment.md).

Delivery integration follows the review stage. Validation checks the review
digest, the plan's `source_commit` and `scope`, every acknowledgement and any
release before dispatch. Dispatch writes `alert-accounting.json` and then calls
`enforce()`, so a held alert stage records its accounting but never writes
`owner-completion.json`. Recovery reloads the durable accounting and requires it
to match the recorded review digest, the ordered alert set and every
acknowledgement's owner and time before re-raising the original hold. An
interrupted alert stage is therefore never completed by a retry.

## Command line

```sh
python tools/operations_review.py --review /private/operations-review.json \
  --output /private/operations-result.json
```

`main` requires the private review and a clean checkout whose commit equals
`source_commit`. It exits 0 only for `OPERATIONS_HEALTHY`; every other outcome,
including a rejected input, exits 2 with `HOLD_OPERATIONS_RECONCILIATION` and
`native_acceptance: false`.

```sh
python tools/operations_alerts.py --review /private/operations-review.json \
  --result /private/operations-result.json \
  --acknowledgements /private/acknowledgements.json \
  --release /private/containment-release.json \
  --output /private/alert-accounting.json
```

`--release` is optional. `main` exits 0 only when no alert is escalated, no
alert is pending and any requested release is authorized; otherwise, and for any
rejected input, it exits 2 with `HOLD_OPERATIONS_ALERTS` and
`native_acceptance: false`.

## Limits

The review is a classification of supplied evidence. It performs no native read,
repair, boundary change or activation, and it does not qualify an observer, a
notification path or an operating authority. The alert accounting is likewise a
record of supplied acknowledgements and release authority: it delivers no
notification, pages no on-call owner, and performs no containment or restoration.
Observer coverage, alert delivery, on-call acknowledgement, containment execution
and production acceptance remain native commissioning evidence under the
[completion backlog](completion-backlog.md).