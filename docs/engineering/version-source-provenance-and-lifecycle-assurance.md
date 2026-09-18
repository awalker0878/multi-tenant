# Version, source provenance and lifecycle assurance

**Purpose:** make G32 executable by separating source review from installed-tuple compatibility and native qualification.

A source edition, documentation review date, provider repository release or Terraform lock selection is not proof that the installed product/API/provider/hardware/licence combination is supported. G32 therefore introduces a distinct exact-tuple provenance record that must be current before native qualification can be current.

## Source obligations

- G32 requires source-review state to remain separate from source edition and requires dated compatibility/lifecycle evidence for the selected installed tuple.
- QUAL-001 requires exact product/API/provider/hardware and applicable feature/licence scope before production placement can rely on qualification.
- NUT-001 illustrates the same rule for provider/resource lifecycle: current supported interfaces are preferred and legacy use requires compatibility rationale.
- SUP-001 requires approved privileged software/provider/module sources, integrity and compromise-response handling.
- VULN-001 requires version/support inventory, vulnerability ownership, exception handling and retirement decisions.
- VULN-002 requires compatibility/regression evidence and a tested recovery strategy for updates; unsupported assets must be controlled at admission.
- VND §7 explicitly states that a source-review date or provider repository version is not evidence that the installed combination is supported.

## Three different evidence states

These are deliberately separate:

1. **Source review** — what exact edition/reference was reviewed, how fully it was accessible, when it was reviewed and when that review must be refreshed.
2. **Tuple compatibility/lifecycle** — whether the exact installed product, API, automation provider, hardware and licensed-feature combination is currently supported and operationally covered.
3. **Native qualification** — what capabilities, assurance profiles, failure cases and tested limits were actually demonstrated on that tuple.

The first two do not substitute for the third. The third is now rejected unless the first two are represented by one matching `CURRENT_SUPPORTED` provenance record.

## Active provenance index

The active index is `sources/capabilities/version_source_provenance_index.json` and is intentionally empty today.

A record binds:

- platform family and stable product-tuple identity;
- exact product and product version;
- exact API and API version;
- exact tested automation-provider versions;
- hardware-profile reference;
- exact feature/licence set;
- source reviews;
- compatibility evidence;
- lifecycle/support evidence and accountable owners.

### Required source kinds

A current supported tuple requires current reviewed evidence for:

- product support;
- API reference;
- automation provider;
- hardware compatibility;
- release notes.

If the tuple claims licensed features, feature-entitlement evidence is also mandatory.

`PARTIAL_ACCESS` and `INHERITED_NOT_REVERIFIED` are valid historical/research states but cannot satisfy a current mandatory source kind. This is how access-limited or inherited material remains visible without being promoted into current support evidence.

### Compatibility record

The compatibility block records a dated compatibility decision and separate evidence for product/API compatibility, provider compatibility, hardware, operation coverage and feature entitlement. Exceptions remain explicit.

Provider lockfiles and interface pins are useful reproducibility evidence, but they are not by themselves compatibility approval.

### Lifecycle record

The lifecycle block records current support status, supporting evidence, review cadence, any known support-end date, vulnerability ownership and an accountable lifecycle decision.

No universal upgrade horizon is invented. A scheduled support end remains an explicit dated condition. Once support has ended, the tuple cannot remain `CURRENT_SUPPORTED`.

## States

Supported states are:

- `CURRENT_SUPPORTED` — all mandatory source kinds are currently reviewed; compatibility and lifecycle evidence are current; support is not unknown or ended.
- `REVIEW_DUE` — source, compatibility or lifecycle review has expired.
- `UNSUPPORTED` — support is explicitly ended or the recorded support-end time has passed.
- `UNCERTAIN` — authoritative support/provenance state requires reconciliation.

Only `CURRENT_SUPPORTED` can back a current native qualification dossier.

## Qualification integration

`scripts/check_platform_qualification.py` now requires exactly one matching `CURRENT_SUPPORTED` provenance record for every `CURRENT_APPROVED` qualification record. Platform family, `product_tuple_id` and the entire product/API/provider/hardware/licence tuple must match exactly.

This prevents:

- qualifying against a documentation snapshot while the installed version differs;
- silently changing an automation-provider version under an old qualification;
- carrying a hardware or entitlement assumption into a different installation;
- leaving a qualification current after support or compatibility evidence expires.

## Readiness preflight

`scripts/check_version_source_readiness.py` checks one planned exact tuple against the active provenance index.

A successful result is `VERSION_SOURCE_PROVENANCE_CURRENT_NO_QUALIFICATION_GRANTED`. It grants no native qualification, site selection, reservation, allocation, apply or activation authority.

Current repository state remains held because the active provenance index is empty:

```sh
python scripts/check_version_source_readiness.py examples/version_source_readiness_intent.json.example --as-of 2026-09-18T22:00:00Z --expected-status HOLD_NO_CURRENT_VERSION_SOURCE_PROVENANCE
```

Actual installed versions, support matrices, current vendor/project material, compatibility decisions and lifecycle ownership remain site/platform-owner work.

[G32 — Version and source provenance](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G32) · [VND §7 — Implementation tuple and decision package](platform-realizations/7-implementation-tuple-and-decision-package.md) · [Native qualification dossier](platform-native-qualification.md)
