# Operational handover and incident-readiness assurance

**Purpose:** make G31's operating ownership, handover and incident-behaviour evidence executable without turning this repository into an ITSM system, privileged-access manager, incident command platform or production operations authority.

Operational readiness is acceptance of a specific service envelope, not receipt of a generic document set or a successful installation. A service can satisfy this dependency only when named operating ownership, privileged-access review, monitoring evidence and a current scoped incident exercise are attributable to the exact WSD/site/service/platform/operating/recovery scope.

## Source obligations

- G31 requires accepted handover, credential review and a scoped incident exercise.
- OPS-002 requires owner/escalation, dependency, recovery, capacity, monitoring, runbook, support/version and evidence records, with privileged access reviewed against the actual authority model.
- DRIFT-001 through DRIFT-003 require security-significant drift to affect current readiness, emergency changes to be reconciled, and containment to override routine reconciliation until explicit release.
- IR-001 and IR-002 require scoped containment, attributable authority, evidence custody, recovery acceptance and explicit containment release.
- ONB-001 requires operational readiness before Service Ready.
- ACPT-001 keeps operational owner acceptance separate from formal authorization.

## Exported assurance record

The active index is `sources/capabilities/operational_handover_assurance_index.json` and is intentionally empty today.

A future record binds one WSD/request to an exact opaque operating scope:

- site;
- service class;
- platform profile;
- operating-model record;
- recovery profile.

### Handover acceptance

The handover record carries an acceptance decision, receiving/support owners, escalation and on-call references, as-built record, dependency set, SLO/recovery record, capacity envelope, runbook set and evidence package. Review cadence is explicit.

### Accountable operating decisions

The record requires separately attributable owners for:

- service change;
- incident containment;
- containment release;
- recovery acceptance;
- shared-foundation change;
- privileged-access decisions.

This prevents a routine workload executor or reconciliation mechanism from silently acquiring incident-command or infrastructure authority.

### Privileged-access and monitoring review

Current evidence requires a reviewed privileged-path/custody record, a tested break-glass reference and no unresolved stale privileged grants. Monitoring evidence must identify service monitoring, alerting and evidence-loss handling and remain inside its validity interval.

### Scoped incident exercise

A current exercise records incident authority, containment scope/evidence, evidence custody, coordination, recovery acceptance, an explicit containment-release decision and reconciliation of any emergency change.

The exercise chronology must show start → containment → attributable release → reconciliation. It must stay within the approved scope rather than relying on a broad unrelated outage. A passing synthetic or historical exercise is evidence only for the scope and time interval it actually represents.

## States and fail-closed behavior

Supported states are CURRENT_ACCEPTED, REVIEW_DUE, EXERCISE_DUE, GAPS_OPEN and UNCERTAIN.

CURRENT_ACCEPTED requires current handover, credential, monitoring and exercise evidence with no OPEN residual obligations. REVIEW_DUE is used when an operating review expires. EXERCISE_DUE is used when the operating reviews remain current but the incident exercise has expired. GAPS_OPEN is reserved for current evidence with unresolved operational obligations. UNCERTAIN blocks reliance until the authoritative state is reconciled.

## Readiness preflight

`scripts/check_operational_handover_readiness.py` compares the reviewed WSD requirement with the exported assurance record.

A successful result is `OPERATIONAL_HANDOVER_CURRENT_NO_OPERATION_AUTHORIZED`. It is only an operational-readiness prerequisite.

It does **not**:

- change privileged access;
- start incident containment;
- release containment;
- execute recovery;
- reconcile an emergency change;
- apply infrastructure;
- activate production.

Current repository state remains held because the active assurance index is empty:

```sh
python scripts/check_operational_handover_readiness.py examples/operational_handover_readiness_intent.json.example --as-of 2026-09-18T21:00:00Z --expected-status HOLD_NO_CURRENT_OPERATIONAL_HANDOVER
```

Actual team/on-call assignments, incident command, privileged-access changes, emergency actions, recovery acceptance and production operating authorization remain external accountable work.

[G31 — Operating ownership and incident behaviour](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G31) · [QUAL §7 — Operating accountability, handover and change](../assurance/site-qualification/7-operating-accountability-handover-and-change.md) · [OPS §8 — Accept operational responsibility](../operations/recovery-transition/8-accept-operational-responsibility-for-the-delivered-scope.md)
