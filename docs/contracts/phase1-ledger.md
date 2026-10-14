# Phase 1 implementation ledger

Scope: contract integrity, dependency closure and release rationalization on
`codex/capability-runtime-assurance-audit-fixes`. Runtime behavior and security
qualification are the subsequent Phase 2; their existing gates remain strict.

## Baseline — 2026-10-14

- Clean checkout at `40eb5d763d104d0fdc33e1e9d8e44bf0793de45b`.
  All five requested starting commits are ancestors of this revision.
- Executed build, authority generation, canonical validation, dependency graph,
  runtime binding coverage and all ten Git-backed publication tests: PASS.
  Inventory: 75 active releases, 166 HTTP operations, 33 installed copies.
  Graph: 15 declared canonical dependencies and 103 consumer relationships;
  78 relationships have no installed loader and require separate evidence.
- Installed the pinned contract validators and five editable Python packages.
  Initial unittest run before package installation finished had 13 environment
  errors (Python imports and absent PHP); rerun after installation is underway.
  PHP installation requires correcting the container's apt sandbox user setup.
- CI run `38577108733`: canonical contract job passed (193 tests), all nine
  built image/wheel jobs passed. Service quality jobs fail lint/format/types or
  frontend boundaries; measured runtime assurance fails independently.

## Discoveries and decisions

1. Prior-state retirement blocks previously consumed contracts permanently
   within a PR, even after legitimate consumer removal. Replace that restriction
   with discovery of remaining references using both current and prior bindings.
2. The canonical reference checker ignores YAML, absolute schema identifiers,
   embedded schema dependencies and generated projections. Dependency reporting
   duplicates declarations rather than establishing their independent closure.
3. AsyncAPI payload dependencies and three capability source-manifest links are
   absent from release metadata. Reconcile them against actual files.
4. Keep producer-local validation, generated projections, external consumption,
   installed copies and test/tool validation distinguishable in reports.
5. Do not equate an empty consumers list with an unused release. Source-only
   quality policy schemas and producer-owned events may remain justified.

## Verification and remaining work

Independent discovery, retirement regressions, complete release inventory,
ownership reconciliation, final verification and Phase 2 handoff are pending.
No acceptance criterion is marked complete on the strength of the baseline.
