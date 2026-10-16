# Contract assurance third-pass implementation ledger

Status: **implementation pushed; acceptance gated on CI and external E4 evidence commissioning**. Branch: `codex/capability-runtime-assurance-audit-fixes`. PR #64 remains draft.

| Finding | Implemented and exercised | Acceptance boundary |
| --- | --- | --- |
| P1 Required field disposition drift | Planning and Lifecycle share fail-closed field/workload-ID checks. Wire v2.2 validation profile rejects apparently eligible required unobserved, drifted or unqualified transformed fields. Negative tests include recomputed digests and duplicate workload IDs. | A real independent E4 transformation remains held by the v2 wire; no silent relaxation. |
| P1 Complete application membership | Lifecycle re-reads current published Catalogue intent with its own credential and compares revision, digest, scope and exact unique workload IDs. New missing/stale/extra workload tests. | Catalogue must provision distinct `LIFECYCLE_CALLER_CREDENTIAL_FILE` and Lifecycle native-owner catalogue endpoint. Missing owner/credential is fail-closed. |
| P2 Evidence parity | Planning preview and require compare source/target native installed tuples with independent Inventory-selected review, profile SHA, reviewed digest, and source/owner generation. Lifecycle checks equivalent evidence and current authority. | Enforce exact physical release enrollment in E3/E4 on every effect; do not treat the contract as native write authority. |
| P2 API and event conformance | Active registry expanded to all 19 declared currently consumed contracts, including eight OpenAPI files. Central checker inspects current OpenAPI 3.0/3.1 operations, AsyncAPI channel/address/operation consistency, references and JSON Schema; CI now includes producer-to-consumer contract tests and ASGI route tests. | Full external AsyncAPI 3 parser validation, live broker envelopes, all producer media/status combinations, and GitHub CI must pass before review completion. |
| P2 E4 provenance | New immutable field-provenance v1 schema binds Catalogue revision, workload/field, native profile, requirement and observation SHA, transformation, independent acceptance, expiry, decision and revocation. Negative schema tests. | **Not commissioned:** wire v2 intentionally denies required qualified transformations. An authenticated Assurance provenance-read endpoint and new wire version with independent Lifecycle validation are necessary before enabling them. |

## Acceptance checks

- `python scripts/contracts/generate_readiness.py`
- `python scripts/contracts/build.py --check`
- `python scripts/contracts/check.py`
- `python -m unittest discover -s tests/contracts -p 'test_integrity.py' -v`
- `python -m pytest -q services/inventory/tests/test_migration_collection_coverage.py services/inventory/tests/test_migration_collection_evidence.py services/planning/tests/test_migration_owner_contract.py services/planning/tests/test_migration_readiness.py services/lifecycle/tests/test_migration_readiness.py services/lifecycle/tests/test_native_owners.py`
- P03 Catalogue PostgreSQL integration fixture: assert separate Planning and Lifecycle current-intent callers, denied Governance/unrecognized tokens, and no token reuse.

Do not mark the PR ready, merge, or claim runtime qualification while any required check is queued/failing or E4 source authority remains uncommissioned. Historical canonical v2 readiness and Planning OpenAPI v1.6 remain byte-immutable.
