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

## Implemented corrections

- Shared independent discovery replaces the JSON-only registry scanner and
  reconciles 47 canonical dependency edges, including YAML payloads, URI IDs,
  embedded schemas, source generation and profile/schema relationships.
- All six manifests have bidirectional release/copy bindings; stray partitions,
  duplicate generation ownership and missing inputs fail validation. Inventory's
  source assembler now exclusively owns its installed JSON output.
- Five authority projections use one reconstruction implementation. Planning
  Lifecycle reads explicitly depend on Planning v1.2 and readiness v2.2.
- Retirement discovers surviving prior copy names, typed loader keys, references
  and schema IDs against current files. Real migration/removal passes; deletion
  of declarations alone fails. CI now runs this gate against the actual review
  base, separately from new-publication quality cutover.
- The review against main found all 41 surviving published canonicals byte
  unchanged. Earlier branch work removed 48 main-era releases; this execution
  removes **zero** additional releases. None were proven eligible for removal.
- Found and registered Planning's two dynamic fact schemas. An immutable file
  map makes both loaders discoverable. Wheel/image inspection covers facts,
  nested copies and self-identifying schemas outside conventional namespaces.
  Reviewed local bytecode caches are excluded from authored source comparisons;
  unreviewed packaged bytecode remains rejected.
- Reconciled the Inventory fact consumer to Planning, added four missing
  generated capability-definition consumers, and removed unsupported asserted
  consumers. Validation-only schemas retain their producer and dependency
  relationships without inventing runtime consumers. Current graph: 83
  consumer relationships, 8 producer-local copies, 27 installed-loader edges
  and 56 source-declared relationships.
- Admission impact now follows canonical dependent releases transitively using
  both base/head graphs. Every deployable component must be represented in the
  artifact inventory and CI matrix, including newly added Dockerfiles.
- Fixed the Console boundary's rejection of its own static contract JSON input;
  cross-component and non-contract imports remain denied.
- Updated stale documentation links and retention advice. No Markdown reference
  to an absent canonical release remains. Current wire identifiers and method
  labels retain the mapping required by active service boundaries; no retired
  version acceptance or compatibility adapter is added.

## Executed verification

- Required build, five authority projections, schema/specification validation,
  runtime inventory, 35 installed usage records, dependency graph and runtime
  binding coverage: PASS. Six source manifests, 30 schemas, 166 HTTP operations,
  nine deployable artifact owners. Generation checks for P03/P04/P06/P09,
  capabilities and readiness: PASS.
- Full unittest discovery: **210 passed**. Full pytest contract suite:
  **214 passed**, plus 88 passing subtests. Publication/retirement suite:
  **16 passed**. Dedicated discovery canaries: **14 passed**.
- Locked Python suites: Inventory 214 passed/47 skipped; Lifecycle 375/86;
  Planning 586/20; Inventory worker 146/0; Lifecycle worker 725/27.
  Total: **2,046 passed, 180 infrastructure-dependent skips**. Skips are not
  claimed as executed qualification. Planning was rerun after its loader change.
- Nine-direction synthetic outcome/method validation: PASS. Console frontend
  boundaries: 47 actual source files and 13 positive/negative fixtures PASS.
- Initial missing Python modules, PHP and formatter errors were environment
  defects. Resolved with pinned uv environments, the installed validators,
  formatter PATH and a locally extracted PHP executable. No tests were disabled.
- Actual local builds and attestation of all five wheels: PASS at `eac26512`;
  Planning includes 12 registered copies (including both fact schemas), Lifecycle
  includes eight, and the other three wheels include their verified generated
  product code. Remote CI run `38586116631` at that revision passed CI / Contracts,
  all nine image/wheel builder jobs and the complete runtime-binding aggregation.
  Existing service quality jobs and CI / Contract assurance remain red; no
  overall-CI or runtime-qualification success is claimed.

## External blocker and Phase 1 determination

**Phase 1 FAIL — not complete.** The derived per-release inventory accounts for
75 releases: 74 have repository source-integrity/lifecycle evidence, one remains
`active but requiring correction`. Planning loads the collection manifest through
its independently provisioned `PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE`.
That variable and referenced deployment manifest are absent here. Consequently
their actual canonical identity, enrolled releases, packaging/mount provenance
and supported external commitments cannot be independently verified. Preserve
the active release; do not fabricate deployed evidence or assume retirement safe.

No external deployment access, mounted custody inputs or supported-consumer
commitment inventory was supplied. Repository discovery cannot establish those
facts. The [conditional Phase 2 handoff](phase2-handoff.md) records the exact
input needed and the separately observed runtime conformance gaps.

## Acceptance status

- [ ] Every active canonical release independently verified (74/75 source scope;
  external manifest consumption remains unverified).
- [x] Every active release has a registered owner and justified repository lifecycle.
- [ ] Actual producer/consumer relationships fully reconciled across external deployments.
- [ ] Complete dependency discovery including external mounted custody evidence.
- [x] Registry deletion cannot bypass current/prior repository dependency checks.
- [x] Proven unused releases/artifacts removed; none of the 75 were safely removable.
- [x] No additional historical canonical files, deprecated loaders or shims introduced.
- [x] Current registry/installed-copy/source-manifest inventories agree.
- [x] Generation and actual image/wheel packaging checks passed on the pushed implementation checkpoint.
- [x] Relevant executed Phase 1 regression tests pass.
- [ ] Final closeout-head CI integrity gates verified (checkpoint integrity/artifact gates passed).
- [ ] Final re-audit has no unresolved Phase 1 blocker.
- [x] Documentation, machine-readable inventories and handoff updated.
- [x] Implementation and closeout changes committed and pushed to the working branch; main was not merged.

## Final independent re-audit

- Re-enumerated the current canonical tree and all deployable Dockerfiles;
  checked owners, exact secondary indexes, 47 discovered canonical edges,
  35 registered copies, both generated reports and all source-manifest inputs.
- All 75 initial releases remain; no canonical bytes, external wire paths or
  versions were changed. Zero releases qualified for additional safe removal.
- Re-audit added a retirement regression for legitimate migration of a generic
  resource path to new canonical bytes. A retired versioned filename cannot be
  reused as an alias; both positive/negative cases were executed.
- The external registry input is still absent. The report retains its unverified
  classification and Phase 1 remains FAIL. Native/provider and mounted release
  commitments are explicitly unestablished, not presumed absent.
- `scripts/p09/check_contract.py` exposed an actual Planning response/schema
  conformance failure, documented in the Phase 2 handoff. It was not suppressed
  and no runtime implementation was started to hide that future-phase result.
