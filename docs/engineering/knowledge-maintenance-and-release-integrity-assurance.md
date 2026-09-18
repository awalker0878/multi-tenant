# Knowledge maintenance and release-integrity assurance

**Purpose:** make G34 executable by separating static documentation consistency from an attributable maintained-release decision.

The repository already checks Markdown links, anchors, retained requirement wording, ADR crosswalks, source coverage, generated navigation and repository hygiene. Those checks are necessary but they do not assign a document owner, define a maintenance cadence, resolve semantic duplication/drift, prove a coherent release version set, or approve a change for publication.

## Source obligations

- G34 requires a primary home per topic, stable parent anchors and release-wide link/requirement mapping checks.
- GM §2 defines the eight source-derived knowledge topics and their change-ripple obligations.
- DOC-001 requires stable normative requirement identifiers, owners, applicability, source basis, verification and complete generated catalogues.
- STD-001 requires source edition/review/applicability/owner/supersession maintenance and impact review after source changes.
- STD-002 requires mappings to retain source edition/identity and distinguish source requirements, local translations and design decisions.
- RA §1 and RA §30 keep parent architecture and controlled delivery/change records authoritative over supplements.

## Primary knowledge-home registry

The source-derived routing map is `sources/documentation/knowledge_home_registry.json`.

It represents exactly eight topics:

- site/cell/failure;
- fabric/routing/attachments;
- privileged access;
- tenancy/native platforms;
- service/data/trust/recovery;
- provisioning/change;
- capacity/operations/assurance;
- exceptions/future services.

Each topic binds explicit parent anchors, one primary detail home, optional related homes and its change-ripple statement. The checker verifies every referenced file and explicit anchor, requires the complete topic set, and rejects duplicate primary homes.

This registry routes maintenance. It does not authorize a supplement to override or weaken its parent architecture.

## Static validation versus maintained release

`scripts/check_documentation.py` and `scripts/check_repository.py` already provide strong static validation. G34 adds the missing accountable layer.

A current release-maintenance record requires:

- exact release ID and reviewed Git revision;
- a coherent version-set map for architecture, engineering, requirements, tests, gap register, source reviews, knowledge-home registry and generator;
- a maintaining owner and cadence reference;
- current release-wide documentation/repository/link/requirement/primary-home validation;
- attributable duplicate-policy review;
- attributable parent/supplement drift review;
- scenario-consistency review;
- an approved change record and owner;
- affected knowledge-topic IDs and change-ripple review;
- no unresolved conflicts.

## Version-set integrity

The version-set record intentionally uses repository paths plus the exact reviewed Git revision rather than inventing independent document version numbers. This makes the release evidence revision-specific and prevents a successful report for one tree from silently validating a changed tree.

Every required version-set role must be present and two roles cannot silently alias the same file.

## Duplicate-policy and drift review

Simple text similarity is not treated as authoritative semantic conflict detection. Automated link/ID checks can catch structural duplication, but whether two supplements express conflicting policy or a supplement weakens its parent requires an attributable review.

The release record therefore requires both:

- `duplicate_policy_review_ref`;
- `drift_review_ref`.

Any unresolved issue is retained in `unresolved_conflicts`. A `CURRENT_MAINTAINED` record must have none.

## Change control

Each maintained release records the approved change record, approval reference, accountable owner, affected knowledge topics and change-ripple review. Approval must follow the recorded release validation.

The checker validates chronology and structure only. It does not authenticate a signer or issue publication/architecture approval.

## States

Supported states are:

- `CURRENT_MAINTAINED` — maintenance and validation are current and no unresolved conflicts remain;
- `REVIEW_DUE` — owner/cadence review is stale;
- `VALIDATION_DUE` — maintenance review remains current but release-integrity validation has expired;
- `CONFLICTS_OPEN` — current evidence exists but duplicate-policy or drift conflicts remain unresolved;
- `UNCERTAIN` — authoritative release/maintenance state requires reconciliation.

## Readiness preflight

`scripts/check_knowledge_maintenance_readiness.py` verifies the exact requested release ID, Git revision and complete eight-topic maintenance scope.

A successful result is `KNOWLEDGE_MAINTENANCE_CURRENT_NO_PUBLICATION_AUTHORIZED`.

It does **not**:

- approve or publish a release;
- accept a change;
- reassign a primary knowledge home;
- accept a documentation conflict;
- authorize architecture;
- apply infrastructure;
- activate production.

Current repository state remains held because maintaining owner/cadence and approved release-change evidence have not been supplied:

```sh
python scripts/check_knowledge_maintenance_readiness.py examples/knowledge_maintenance_readiness_intent.json.example --as-of 2026-09-18T21:05:00Z --expected-status HOLD_NO_CURRENT_RELEASE_MAINTENANCE
```

The active maintenance index is therefore intentionally empty even though static repository/documentation checks can pass.

[G34 — Knowledge maintenance and cross-link integrity](../assurance/gap-map/3-detailed-gap-register-and-treatment.md#gap_G34) · [GM §2 — Primary knowledge homes](../assurance/gap-map/2-primary-knowledge-homes-and-cross-cutting-changes.md#GM_s_002) · [Documentation migration and maintenance](../DOCUMENTATION_MIGRATION.md)
