# Control inheritance and external-dependency assurance

**Purpose:** make G30's control-allocation and inheritance evidence executable without turning this repository into a control-assessment system, organizational authority, risk register or authorization service.

A control-family crosswalk is not a completed assessment. A service can satisfy this readiness dependency only when the reviewed WSD scope has attributable control allocation, time-bounded evidence, explicit external interfaces and residual-gap decisions that apply to the actual site, service, platform profile, catalogue and control selection.

## Source obligations

- G30 requires provider, tenant, shared and inherited dispositions plus accepted external-control evidence and residual-gap decisions.
- AUTH-001 keeps technical conformance, service readiness and formal authorization as distinct states; CI cannot create or renew authorization.
- STD-001 requires edition/applicability/owner/review provenance for adopted standards and control sources.
- STD-002 prevents family-level mappings from being represented as completed control assessment.
- QUAL §6 requires the hosting design to distinguish provider implementation, tenant implementation, shared responsibility and accepted inheritance.
- RA §28 requires formal authorization to remain with the designated authority after applicable control tailoring and assessment.

## Exported assurance record

The active index is `sources/capabilities/control_inheritance_assurance_index.json` and is intentionally empty today.

A future record binds one WSD/request to an exact opaque scope:

- site;
- service class;
- platform profile;
- control catalogue/edition record;
- reviewed control-selection record.

The record also carries the external allocation decision, accountable role, acceptance/review dates, individual control allocations, all six organizational interfaces from QUAL §6, residual gaps and repository source references.

### Per-control allocation

Each control allocation records:

- stable source control identifier;
- parameter-decision reference;
- PROVIDER, TENANT, SHARED or INHERITED responsibility;
- implementation, evidence and evidence-scope references;
- accountable owner references;
- observation and evidence-validity times.

INHERITED is special: it requires an explicit inherited-service reference. Non-inherited controls are prohibited from carrying that field. This prevents a provider implementation or shared responsibility from being silently relabelled as inherited evidence.

The repository stores opaque evidence references, not assessment payloads, personal records, facility records, credentials or native control-system objects.

### External organizational interfaces

QUAL §6 identifies six interfaces that must not disappear from infrastructure evidence:

1. physical/environmental;
2. personnel and privileged roles;
3. maintenance and support;
4. training and operations;
5. data/privacy/location;
6. assessment and authorization.

A current record must represent each exactly once with an accountable external-owner reference, evidence reference, applicability reference and evidence-validity interval. Evidence from a supplier/shared service is not reusable merely because the product name matches; applicability remains scoped to the actual service, site, version, tenant scope and time interval.

### Residual gaps

Residual gaps are explicit records tied to allocated controls.

OPEN gaps require an owner and treatment reference and cannot carry an acceptance decision. ACCEPTED gaps require an attributable external decision reference. The checker validates the shape and chronology only; it does not decide whether a risk should be accepted.

## States and fail-closed behavior

Supported states are CURRENT_REVIEWED, REVIEW_DUE, GAPS_OPEN and UNCERTAIN.

CURRENT_REVIEWED requires:

- current allocation review;
- current per-control evidence;
- current external-interface evidence;
- no OPEN residual gaps.

REVIEW_DUE requires at least one expired review/evidence interval. GAPS_OPEN is reserved for current evidence with unresolved residual gaps. UNCERTAIN blocks reliance until the authoritative state is reconciled.

## Readiness preflight

`scripts/check_control_inheritance_readiness.py` compares a reviewed WSD requirement with the exported assurance record.

A successful result is `CONTROL_INHERITANCE_EVIDENCE_CURRENT_NO_AUTHORIZATION_ISSUED`. It means only that the exact requested scope contains all required control IDs under a current reviewed evidence record.

It does **not**:

- select catalogue controls or parameter values;
- accept inherited evidence;
- close or accept residual risk;
- issue, renew or impersonate formal authorization;
- apply infrastructure;
- activate production.

Current repository state remains held because the active assurance index is empty:

```sh
python scripts/check_control_inheritance_readiness.py examples/control_inheritance_readiness_intent.json.example --as-of 2026-09-18T20:00:00Z --expected-status HOLD_NO_CURRENT_CONTROL_ALLOCATION
```

Actual control tailoring, named organizations, inherited assessments, personnel/facility/maintenance evidence, residual-risk decisions and formal authorization remain external accountable work.

[QUAL §6 — Control inheritance and organizational interfaces](../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md) · [G30 — Control inheritance and external dependencies](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G30) · [RA §28 — Architecture acceptance and verification](../architecture/reference/28-architecture-acceptance-and-verification.md)
