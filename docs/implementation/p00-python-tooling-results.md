# P00.03 Python tooling compatibility results

Executed 2026-10-04 against Python 3.12.14 on Linux x86-64. The isolated spike successfully installed a locked Python quality-tool set, linted and type-checked the fixture, ran four behavior tests, and enforced three Import Linter contracts. Seven deliberately invalid source changes were rejected for their intended dependency rule. This is measured P00.03 feasibility evidence; it does not complete G00.03, approve the production runtime, or supply G01 evidence for services that have not been implemented.

## Scope and current direction

The code lives under [spikes/compatibility/python](../../spikes/compatibility/python/pyproject.toml), outside every product source root. `probe_inventory` and `probe_planning` are synthetic namespaces representing two independently owned services. Their sample revision transition is disposable test behavior, not an Inventory or Planning feature, migration driver, product contract, or persistence implementation. The real service layout remains the [current architecture convention](../architecture/context-code-structure.md#7-python-services-and-site-workers). The preferred pragmatic Laravel convention is unchanged and is deliberately not imposed on Python.

The fixture exercises the existing Python rules: Domain owns a plain value and invariant; Application uses an owned typed persistence port; Infrastructure provides a memory implementation and may use HTTPX; Interfaces validates a synthetic transport payload using Pydantic and invokes the use case; Bootstrap binds entrypoints and adapters. The positive fixture contains both actual external-library imports, so the external prohibition is tested against packages present in the analyzed graph.

No product service imports this spike. No platform, database, broker, Temporal service, credential, or native operation is involved. The HTTPX smoke continues to use an in-memory mock transport. No legacy application code was copied.

## Historical source review

The requested `implementation/all-waves` reference was inspected at immutable commit `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e` using the GitHub connector.

| Source and blob identity | Information used | Disposition in this spike |
| --- | --- | --- |
| [Historical pyproject.toml](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/pyproject.toml), blob `e160485bab8a2e665843e303e0caa2e69b9c8dfa` | Python `>=3.12`, exact runtime dependencies, optional control-plane dependencies, and many entrypoints under the former `provisioner` package | Retain explicit dependency identity and independent execution evidence. Do not inherit the single-package architecture, dependency set, selected infrastructure, or historical test claims. Python 3.12.14 here continues the current spike family and remains subject to ADR-003. |
| [Historical engineering TAD](https://github.com/awalker0878/multi-tenant/blob/a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e/docs/engineering/TAD.md), blob `ad51d70454cbcfd0071a943478bf844496b26631` | A navigation/composition view of earlier design sources and technical ownership concerns | Keep the current documents authoritative. The old navigation page supplies context, not a recovered architecture baseline or proof that those linked platform chapters were qualified here. |

The historical optional HTTPX version was also 0.28.1. The measured current lock, rather than that coincidence, establishes this spike's dependency identity. Historical Temporal/FastAPI/database libraries were not added merely because they appeared in the old manifest.

## Exact tested tuple

| Component | Measured version | Role |
| --- | --- | --- |
| CPython | 3.12.14 | Isolated execution family; production selection still open |
| uv | 0.12.19 | Lock check, fresh environment installation, export and installed-dependency consistency |
| Ruff | 0.16.10 | Lint rules `E`, `F`, `I`, `B`, `UP`; formatting check; Python 3.12 target |
| mypy | 2.4.0 | Strict checking, no blanket missing-import suppression; 26 Python source/test/helper files |
| pytest | 9.1.1 | Four synthetic behavior tests with strict configuration and marker handling |
| Import Linter / Grimp | 2.15 / 3.17 | Real import-graph analysis against the explicit dependency contracts |
| pip-audit | 2.10.1 | Known-advisory lookup for the exported locked dependencies |
| Pydantic / HTTPX | 2.13.5 / 0.28.1 | Existing library probe, plus legal boundary-layer imports |

Quality tools are exact-pinned in [pyproject.toml](../../spikes/compatibility/python/pyproject.toml); transitive versions and artifact hashes are in [uv.lock](../../spikes/compatibility/python/uv.lock). The resolver covers 51 packages including the virtual project and platform-conditional dependencies; 49 packages were installed for this Linux environment. No claim is made that this is the latest or approved production tuple.

The final manifest SHA-256 is `de0380f117644ebd949e317b5885ea5bc40c352d622bf9ca9fbdb00e7af50697`; lock SHA-256 is `66070660564e8e83a8a27d5c7b149a1f6ae591b8a948b04a2fc058db55fdc302`. Each command record includes the contemporaneous source/configuration hashes, exact arguments, timestamps, actual exit code and stdout/stderr. The clean installation used a newly created temporary environment outside the repository. A package cache may supply verified artifacts; the environment itself was new. Existing compatibility records were preserved. The [artifact inventory](../../spikes/compatibility/results/python-tooling/artifact-inventory.json) binds the final source hashes and all 15 new command records. The audit export contains exact version pins without wheel hashes because it is advisory lookup input, not an installation file; the original uv lock retains installation artifact hashes.

## Commands and results

All commands ran from `spikes/compatibility/python`. The record links retain the explicit temporary environment path and `PYTHONPATH=src` where used. After installation, `uv run --frozen --no-sync` ensured checks used that installed environment without an implicit dependency refresh.

| Check | Recorded command or check | Result and evidence |
| --- | --- | --- |
| Lock consistency | `uv lock --check --index-url https://pypi.org/simple` | PASS; [01](../../spikes/compatibility/results/python-tooling/01-lock-check.json) |
| New environment install | `uv sync --locked --python 3.12 --index-url https://pypi.org/simple`, with a new `UV_PROJECT_ENVIRONMENT` path | PASS; [02](../../spikes/compatibility/results/python-tooling/02-clean-install.json) |
| Runtime and installed version inventory | Interpreter/platform metadata plus package versions; `uv --version` | Captured; [03](../../spikes/compatibility/results/python-tooling/03-environment.json), [14](../../spikes/compatibility/results/python-tooling/14-package-manager.json) |
| Lint | `ruff check .` | PASS; [04](../../spikes/compatibility/results/python-tooling/04-lint.json) |
| Formatting | `ruff format --check .` | PASS, 26 files; [05](../../spikes/compatibility/results/python-tooling/05-format.json) |
| Strict typing | `mypy --no-incremental` | PASS, 26 files; [06](../../spikes/compatibility/results/python-tooling/06-types.json) |
| Behavior | `pytest -q` | PASS, 4 tests; [07](../../spikes/compatibility/results/python-tooling/07-behavior.json) |
| Legal dependency graph | `lint-imports --config .importlinter --no-cache --no-logo` | PASS, 3 contracts, 26 analyzed graph files and 14 dependencies; [08](../../spikes/compatibility/results/python-tooling/08-positive-boundaries.json) |
| Deliberately illegal dependency graphs | `python boundary_probe.py` | PASS, 7 expected rejections; [09](../../spikes/compatibility/results/python-tooling/09-negative-boundaries.json) |
| Original library probe | `python smoke.py` | PASS; [10](../../spikes/compatibility/results/python-tooling/10-library-smoke.json) |
| Installed dependency compatibility | `uv pip check --python <isolated-python>` | PASS, 49 installed packages; [11](../../spikes/compatibility/results/python-tooling/11-dependency-consistency.json) |
| Exact audit input | `uv export --frozen --format requirements-txt --no-emit-project --no-hashes --output-file <temporary-requirements>` | PASS; exported requirements retained in stdout; [12](../../spikes/compatibility/results/python-tooling/12-export-lock.json) |
| Advisory lookup | `pip-audit --strict --disable-pip --no-deps --requirement <temporary-requirements> --format json --progress-spinner off` | PASS, 49 packages audited and zero known advisories returned; strict result [15](../../spikes/compatibility/results/python-tooling/15-strict-advisories.json), initial lookup [13](../../spikes/compatibility/results/python-tooling/13-advisories.json) retained separately |

The behavior tests verify legal composition, immutable input and exactly one saved updated value, rejection before persistence, and strict transport payload validation. They do not prove database transactions, tenancy, authorization, distributed messaging, or native workflow safety.

## Boundary coverage and limits

[The Import Linter configuration](../../spikes/compatibility/python/.importlinter) combines exhaustive layers, independent service roots, and a forbidden external-library rule. The middle layer uses independent Infrastructure and Interfaces siblings. Bootstrap may depend on both, but Interfaces cannot invoke the concrete memory adapter. Missing required layer modules and extra unclassified first-party modules must not silently disappear from coverage.

[The negative-case runner](../../spikes/compatibility/python/boundary_probe.py) copies only the fixture source and configuration into a separate temporary directory for each case. It then injects one violation and invokes the installed Import Linter with caching disabled. Success requires exit code 1, the expected contract marked `BROKEN`, and the offending module in the diagnostic. A generic process failure, missing executable, configuration error or unrelated failing contract cannot satisfy this check.

| Deliberate violation | Expected rule |
| --- | --- |
| Domain imports its Application through a relative aliased import | Owned Python layer direction |
| Application imports its concrete Infrastructure implementation through an alias | Owned Python layer direction |
| Interfaces imports Infrastructure through a relative import | Owned Python layer direction |
| Planning imports Inventory's private Domain type | Independent service sources |
| Domain imports HTTPX | No transport libraries in core |
| Application imports a Pydantic transport model | No transport libraries in core |
| A new unclassified module appears inside a service package | Owned Python layer direction, exhaustive coverage |

This is source-graph evidence for these exact fixtures. The external rule covers the two libraries in this experiment, not a comprehensive future framework/SDK inventory. It does not prove absence of dynamic imports, native effects, undeclared runtime path mutation, shared database access or unregistered build inputs. The current repository registry/AST checks remain complementary. P01 must map actual registered services, workers and packages into complete language-aware rules, exercise generated clients and external SDKs, preserve legal bootstrap behavior, and test the actual build artifacts. Registry success and this spike cannot replace those checks.

## P00 disposition and remaining work

The tested tool tuple is a feasible Python quality-tool candidate for ADR-003 and P01 planning. An accountable engineering review still has to adopt the baseline and its update ownership. Keep P00.03 and G00.03 open until their other runtime, infrastructure, trust, custody and contract-generation choices have recorded decisions and evidence. Do not mark any Python business service implemented from these results.

Before service acceptance, run the selected rules against real source and locks, bind required CI checks to the repository's reviewed protection settings, and verify production image identities and supported architectures. Restricted-network mirrors and advisory freshness require separate evidence: the public PyPI path used here is not an approved production dependency path. A known-advisory lookup is time-specific and does not establish source trust, absence of vulnerabilities, an OS image audit, or a licence/SBOM review.

To reproduce, create a fresh temporary environment, set `UV_PROJECT_ENVIRONMENT` to it and `PYTHONPATH=src`, install from the unchanged lock, then run the command sequence above. Use a new result name with `python record_tooling.py <name> -- <command>`; existing evidence names cannot be overwritten. Capture dependency updates as new experiments. The [delivery register](delivery-register.yaml), [overall compatibility report](p00-compatibility-results.md), [ADR-003](../decisions/adr-003-runtime-and-dependency-baseline.md) and [G00 review](../qualification/gate-reviews/g00.md) remain authoritative for status.

## Primary tooling references

Reviewed 2026-10-04. Upstream documentation supports configuration semantics; the measured records above establish this project's actual result.

- [uv project workflow](https://docs.astral.sh/uv/guides/projects/) — lock and environment operations.
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/) — project settings and rule selection.
- [mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html) — strict type-checker settings.
- [pytest configuration](https://docs.pytest.org/en/stable/reference/customize.html) — strict configuration and test discovery.
- [Import Linter layers](https://import-linter.readthedocs.io/en/stable/contract_types/layers/), [forbidden imports](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/) and [independence](https://import-linter.readthedocs.io/en/stable/contract_types/independence/) — complementary graph contracts and exhaustive layer coverage.
- [PyPA pip-audit](https://github.com/pypa/pip-audit) — advisory lookup, strict dependency collection and scope limits.
