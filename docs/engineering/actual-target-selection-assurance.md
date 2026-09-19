# Actual target selection and restricted native-campaign assurance

**Purpose:** close the I02 recording gap without selecting a site, product, security edge or credential on behalf of the accountable owners.

The repository already knows how to validate exact version/source provenance, native qualification, security-edge assurance, bootstrap dependencies, readback/reconciliation and activation readiness. What remained missing was a controlled record saying **which actual site/cell and installed implementation tuple the native campaign is allowed to contact**.

This gate records that external decision. It does not make the decision.

## Source obligations

- IK §1 requires a restricted qualification fixture and authorized disposable scope before native execution.
- VND §7 requires the exact hardware/firmware, product/API/provider, features/licences, network/storage backends, management topology and ownership to be controlled before an implementation is offered.
- GM §4 keeps site/cell topology, vendor implementation tuple, security-edge implementation, offered family and ownership decisions explicitly open until actual owners select them.
- QUAL-001 requires an exact installed product/API/provider/hardware tuple before production qualification; target selection is earlier and does not itself qualify the tuple.
- ASSUR-003 keeps parameters, owners, test scope and evidence freshness explicit.
- SUP-001 requires approved privileged tooling/source provenance before native privileged execution.

## Active assurance index

The active index is `sources/capabilities/target_selection_assurance_index.json` and is intentionally empty.

A future record binds one `selection_id` to the actual native-campaign target and exact external authority references.

## Selection scope

The scope block records:

- actual site;
- actual cell;
- restricted campaign scope;
- change authority;
- target-contact authority and validity;
- stop authority;
- accountable owner;
- selection and review dates.

A current record means those references were supplied and are current. It does not make this repository a change authority or target-access broker.

## Exact implementation tuple

The selected target record captures:

- platform family (`NUTANIX`, `VMWARE_NSX` or `OPENSTACK`);
- stable product-tuple ID;
- hardware inventory;
- product/API/provider combination;
- feature/licence entitlement;
- version/source-provenance record;
- security-edge realization;
- management/OOB context;
- network backend;
- storage backend.

These are controlled references, not guessed defaults. Selecting a target does not make the tuple `CURRENT_SUPPORTED` or `CURRENT_APPROVED`; the version/provenance and native-qualification gates remain separate.

## Restricted native-campaign boundary

The campaign block records:

- qualification-campaign reference;
- exact native API scope;
- observer scope;
- writer scope;
- credential custody reference;
- controlled evidence workspace;
- data restrictions;
- permitted operations;
- prohibited operations;
- cleanup procedure;
- approved contact window;
- `production_authority_status = NOT_ISSUED`.

No literal credentials, secrets or target endpoint values belong in this index.

## States

Supported states are:

- `CURRENT_SELECTED` — selection review and target-contact authority are current with no OPEN gaps;
- `REVIEW_DUE` — selection or residual-gap review expired;
- `CONTACT_AUTHORITY_DUE` — selection remains reviewed but target-contact authority expired;
- `GAPS_OPEN` — current selection/contact evidence exists but unresolved selection gaps remain;
- `UNCERTAIN` — authoritative target/scope/owner/contact state requires reconciliation.

## Readiness preflight

`scripts/check_target_selection_readiness.py` evaluates one exact site/cell/campaign/platform/tuple selection.

A successful result is `TARGET_SELECTION_CURRENT_NO_TARGET_CONTACT_AUTHORIZED`.

That result still keeps all of the following false:

- target selection by CI;
- target contact;
- credential retrieval;
- native test execution;
- infrastructure apply;
- production activation.

Current repository state remains held because no site/cell/platform target has been selected by the accountable owners:

```sh
python scripts/check_target_selection_readiness.py examples/target_selection_readiness_intent.json.example --as-of 2026-09-19T15:30:00Z --expected-status HOLD_NO_CURRENT_TARGET_SELECTION
```

Once a genuine target is selected, that selection can seed the later version/provenance, qualification, ZIP, bootstrap, readback and other native evidence campaigns without silently changing their separate acceptance criteria.

[IK §1 — Implementation workplan](../implementation/delivery-guide/1-implementation-workplan-and-required-inputs.md) · [VND §7 — Implementation tuple](platform-realizations/7-implementation-tuple-and-decision-package.md) · [GM §4 — Open decision package](../assurance/gap-map/4-open-decision-package-for-implementation.md)
