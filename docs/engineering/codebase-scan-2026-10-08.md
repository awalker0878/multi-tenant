# Codebase scan and corrective commits — 2026-10-08

## Scope and source

The scan started from GitHub `main` commit `7aa94b1e370a0f57aa578b530abb73aa7843df21`, tree `b86e1b1438118d13084ec69ba90cf33b929da1b8`. An isolated local checkout was checked against that exact tree. Corrections are published as individual commits in [PR 62](https://github.com/awalker0878/multi-tenant/pull/62).

All nine deployable components were reviewed, together with contracts, architecture declarations, deployment files, workflows, verification scripts, documentation validators and compatibility experiments. Generated resources were checked against their producers. Installed dependencies and historical evidence were not treated as editable application source. Historical qualification observations were preserved.

## Confirmed defects corrected

| Area | Corrections |
| --- | --- |
| Console | Remove dependencies on deleted campaign members; clear endpoint selections when sites change and discard late responses; refresh readiness values and revision together; bound migration-support polling and mark stale observations; typecheck all browser suites; use vendor-neutral migration navigation. |
| Planning | Expire plans with required capability evidence; require one actor for plan comparison; reject ambiguous disks and incomplete datasets; bound and protect policy registry reads; quarantine ambiguous messages. |
| Inventory | Preserve any-to-any fleet visibility while selecting explicitly profiled test members; paginate policies beyond 50; reject malformed native objects and duplicate identities; require boolean authorization decisions. |
| Lifecycle service | Close completed native grants; preserve terminal success against late holds; restore successfully reconciled campaign members; recheck reduced capacity at effect boundaries; reject nonfinite JSON numbers. |
| Lifecycle worker | Permit empty rootfs files while retaining nonempty disk validation; accept compact Keystone IDs; reconcile durable VMware/AHV VM receipts; validate actual Prism task ID syntax. |
| Governance | Preserve approval-expiry transitions when denying execution; reject approval requests/decisions at the exact expiry boundary. |
| Catalogue | Require typed boolean sharing flags and strictly typed, order-independent authority scope matching. |
| Assurance | Return validation errors for malformed evidence; protect and bound qualification registry reads; compare scope values strictly; inject the secret reader through an Application contract and retain dependency-layer enforcement. |
| Runtime | Load mounted database passwords in Governance and Assurance consistently with deployed configuration; provide distinct migrator credentials to the recovery fixture and mounted files to subprocess tests. |
| Contract tooling | Freeze each artifact at its first publication; restore modified historical artifacts; release added outcome fields as `planning-migration-v1.5` and `tranche-v1.1`; keep consumer resources synchronized. |
| Verification | Exclude installed packages from authored Markdown link checks; package exact contract fixtures for isolated component tests; validate live Inventory responses against current v1.8. |

Fixes address existing requirements for authorization, tenant/scope isolation, durable execution, evidence integrity, API compatibility and independent builds. No service ownership boundary, dependency lock or native qualification decision is widened by these changes.

## Local verification

Tests exercised the changed checkout, not the earlier dependency-cache checkout. Python component suites used explicit source paths and the existing pinned dependency environments. Separate component-only copies reproduced the CI packaging boundary for Inventory and Planning.

| Suite | Passed | Skipped | Additional checks |
| --- | ---: | ---: | --- |
| Inventory service | 159 | 47 | Ruff, format, strict mypy, isolated package collection |
| Inventory worker | 123 | 0 | Ruff, format, strict mypy |
| Planning | 380 | 6 | Ruff, format, strict mypy, isolated package collection, schema drift |
| Lifecycle service | 365 | 72 | Ruff, format, strict mypy |
| Lifecycle worker | 692 | 27 | Ruff, format, strict mypy |
| Console P08 browser regression suite | 13 | 0 | Typecheck, production build, boundary fixtures |
| Documentation regression suite | 91 | 0 | Generated views, links, registry validation |
| P01 script tests | 91 | 0 | Component selection and verification utilities |
| Admission policy tests | 37 | 0 | Existing enforcement retained |
| Artifact release/campaign tests | 8 | 0 | Local non-signing tests |
| Contract history tests | 7 | 0 | Corruption, restoration, merge, deletion and incomplete-history cases |
| P10 script tests | 19 | 0 | Existing operating qualification checks |
| Recovery script tests | 13 | 0 | Existing custody checks |
| P09 retained-evidence tests | 3 | 0 | Existing evidence checks |
| Python compatibility spike | 4 | 0 | Ruff and strict mypy |
| P06 replay resource lifetime | 2 | 49 | Explicit executor shutdown; live/database integration remains CI-only |

The 152 component database skips and 49 P06 integration skips are explicit: this workspace cannot switch to the unprivileged identity required by its PostgreSQL fixtures. They are not passes. PHP, container, broker, Temporal and signing integration require their existing CI runtimes. CI observations and any remaining gate status are recorded in the PR.

P07/P08/P09 contract checks additionally exercised 270 directional workflow scenarios, 3,348 stage boundaries, 1,080 denied-support cases and 720 denied partial-acceptance cases. Script syntax scans covered Python, shell, JSON and YAML. These synthetic cases do not establish installed-platform support.

## CI findings and limits

The starting commit had confirmed native-migration test and published-contract failures. CI during the scan additionally exposed package-external fixture reads, an Assurance dependency-layer violation and import ordering error, and a stale P04 live schema. These have corrective commits and regression coverage; final run results must be read against the PR head.

A P06 replay process reported all four histories replayed successfully and then exited with SIGSEGV. A successful output file does not override an abnormal process exit. Replay now reuses one explicitly managed executor and joins it before writing the report; fault-handler diagnostics remain enabled for any recurrence. The exact native crash cause is unproven, and this observation requires a clean process-level rerun. No retry or ignored exit status converts it to a pass.

The trusted-base admission check reports `review_roles_unconfigured`. Actual reviewer identities and independent role approval are repository governance inputs; this scan does not invent reviewers or weaken the gate. The legacy `catalogue-v1.json` is preserved as an immutable historical artifact with a known OpenAPI defect; its valid published successor is `catalogue-v1.0.1.json`.

No production credentials, native VMware/OpenStack/AHV campaign, installed-platform qualification, container vulnerability scan or independent operating acceptance is claimed. Passing the available tests establishes the reported checks, not a proof that every possible defect is absent.
