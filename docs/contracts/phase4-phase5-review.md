# Contract framework: Phase 4 and Phase 5 implementation assessment

Date: 2026-10-12  
Branch: `codex/capability-runtime-assurance-audit-fixes`  
Pull request: [#64](https://github.com/awalker0878/multi-tenant/pull/64) — draft

## Phase 4 — executable capability qualification

The published capability release currently declares five migration methods and
six operational modes. The worker E2 tests exercise each method-mode combination
and typed method-plan validators. The qualification gate:

- consumes an executed worker JUnit file after the locked P08/Contract Integrity
  worker test command succeeds;
- rejects missing, failed, skipped and duplicated testcases and suites reporting
  failures or errors;
- requires the exact registered native data-method implementations, disallowing
  invented, removed or unimplemented method aliases;
- requires each native method-stage combination to have measured dispatch cases
  for every VMware, AHV and OpenStack source/target direction (nine cases);
- checks complete negative method faults and independent dataset readback
  variants, source capture, durable partial receipts and revocation;
- produces a source-revision and JUnit-digest-bound **E2-only** result with
  `installed_provider_qualified=false` and `native_write_authorized=false`.

The E2 result **does not** establish that real installed VMware, AHV or
OpenStack implementations, native API entitlement, external backup/replication
connectors, guest boot or application datasets have passed E3. They require
commissioned independent provider measurements and E4 receiving-owner signoff.
No compatibility layer or fake provider approval was introduced.

## Phase 5 — one framework with independent invariants

`scripts/contracts/check.py` is an orchestrator, and the active invariants
have separate ownership:

| Module | Responsibility |
| --- | --- |
| `check_schema.py` | Current schema IDs, canonical definitions and embedded projections |
| `check_events.py` | Event declarations, channel/discriminator binding and payload references |
| `check_registry.py` | Canonical registration, owner-operation bindings, retired paths and all installed copies |
| `check_http.py` | Native authority, implemented owner APIs, UUID and error contracts |
| `route_conformance.py` | Actual bounded runtime router conformance |
| `runtime_inventory.py` / `installed_usage.py` | Real consumer-loader and packaging evidence |

The former hard-coded three-copy byte test and source-regex route test were
removed. Comprehensive runtime-copy parity, generated-client checks, route
conformance, quality gates and retirement decisions remain enforced by CI.
Tests were updated to import their genuine owner modules, not a proxy.

### Historical external review

`retirement_report.py` enumerates the retirement manifest, validates its
decision records and emits an actionable artifact with each pending external
inventory, compatibility and independent-review obligation.

The 53 historically deleted canonical versions remain uncleared. This is
**not** an assertion that external consumers do or do not exist. The archive
remains in Git. Completing the review requires real independent evidence:
no generated JSON, repository static scan or blanket approval can replace it.

CI workflow_dispatch can use `require_retirement_clearance=true` to reject an
unresolved review backlog. Normal structural checks still reject new unapproved
deletions and stale executable references while permitting the known,
explicitly documented historical review debt.

## Verification

The following checks must complete successfully for the final commit before
the engineering work is treated as verified:

```sh
python -m unittest discover -s tests/contracts -p 'test_capability_qualification.py' -v
python -m unittest discover -s tests/contracts -p 'test_retirement_report.py' -v
python -m unittest discover -s tests/contracts -p 'test_integrity.py' -v
python scripts/contracts/check.py
python scripts/contracts/retirement_report.py
# Run P08 with locked dependencies and disposable PostgreSQL:
python scripts/p08/qualify.py --output /tmp/p08-qualification
```

Keep PR #64 draft until these checks pass and any legitimate failures are fixed.
Do not claim E3/E4 qualification or external retirement clearance from an E2
passing result.
