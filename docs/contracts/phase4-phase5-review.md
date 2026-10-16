# Contract framework: Phase 4 and Phase 5 implementation assessment

Date: 2026-10-14  
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
- checks exact negative method faults and all 12 independent dataset-readback
  variants by identity (not merely by count), plus source capture, durable
  partial receipts and revocation;
- verifies JUnit-declared suite and root test totals match executed cases;
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
| `check_registry.py` | Active canonical registration, owner-operation bindings and installed copies |
| `check_http.py` | Native authority, implemented owner APIs, UUID and error contracts |
| `route_conformance.py` | Actual bounded runtime router conformance |
| `runtime_inventory.py` / `installed_usage.py` | Real consumer-loader and packaging evidence |

The former hard-coded three-copy byte test and source-regex route test were
removed. Comprehensive runtime-copy parity, generated-client checks, route
conformance and quality gates remain enforced by CI.
Tests were updated to import their genuine owner modules, not a proxy.

### Active-only release inventory

The checkout ships only current canonical releases, active installed copies and
executable consumer bindings. Historical retirement manifests, six obsolete
contract-compatibility snapshots, and archived compatibility tests are not part
of the release. Retained P08 E2 verification no longer reads a frozen contract
baseline or emits an original-contracts count; the current registry and
source-bound executable checks own that invariant. New contract publications
still require the current strict quality profile and semantic comparison.

## Verification

The following checks must complete successfully for the final commit before
the engineering work is treated as verified:

```sh
python -m unittest discover -s tests/contracts -p 'test_capability_qualification.py' -v
python -m unittest discover -s tests/contracts -p 'test_integrity.py' -v
python scripts/contracts/check.py
# Run P08 with locked dependencies and disposable PostgreSQL:
python scripts/p08/qualify.py --output /tmp/p08-qualification
```

Keep PR #64 draft until these checks pass and any legitimate failures are fixed.
The 2026-10-14 CI run still reports incomplete release/operation assurance and
unrelated service quality failures. Source cleanup must not bypass those gates.
Do not claim E3/E4 qualification from an E2 passing result.
