# P01 Python service and worker foundations

Package: P01.01. Requirement: R02. Gate criterion: G01.01, partial evidence. Execution date: 2026-10-04. Author/executor: Codex. This increment implements Inventory and Lifecycle package boundaries and one independently packaged diagnostic for each context's selected worker boundary. The existing [Planning bootstrap](p01-planning-bootstrap.md) remains a separate artifact and evidence record.

## Implemented packages

| Package root | Distribution and import module | Installed diagnostic | Ownership |
| --- | --- | --- | --- |
| `services/inventory/` | `product-inventory`; `inventory` | `inventory-health` | Inventory service |
| `services/lifecycle/` | `product-lifecycle`; `lifecycle` | `lifecycle-health` | Lifecycle service |
| `workers/inventory/` | `product-inventory-worker`; `inventory_worker` | `inventory-worker-health` | Inventory-owned collection boundary |
| `workers/lifecycle/` | `product-lifecycle-worker`; `lifecycle_worker` | `lifecycle-worker-health` | Lifecycle-owned execution boundary |

Every package has its own manifest, lock, Python selection, wheel metadata, tests and installation entrypoint. Runtime dependencies are empty. Package imports are inert. Bootstrap composes the diagnostic interface; there is no copied business model or shared runtime business library. Actual Domain, Application and Infrastructure modules will be introduced with their implemented responsibilities under the [Python context convention](../architecture/context-code-structure.md#7-python-services-and-site-workers).

Worker ownership follows the [context registry](../../architecture/context-map.yaml). These diagnostics do not depend on their owner service package. Any future reuse of owner code must explicitly include a compatible immutable artifact or build input; a runtime sibling-directory import remains prohibited. Worker ownership supplies no independent database or native authority.

## Diagnostic behavior

Each command accepts exactly `liveness` or `readiness`. Liveness exits 0 with `scope=process_bootstrap`: it establishes only that this short-lived command loaded. Service readiness exits 1 with `service_dependencies_not_implemented`; worker readiness exits 1 with `worker_dependencies_not_implemented`. Neither kind runs a persistent server or consumes tasks. Both responses declare `native_operations_enabled=false`.

Worker responses also identify their owner in `service`, their registered `inventory-workers` or `lifecycle-workers` identity in `component`, `component_kind=worker_bootstrap`, and `task_consumption_enabled=false`. Unknown, missing or extra arguments, including a readiness `--force` override, exit 2 without a success payload. A successful diagnostic cannot be used as dependency-readiness or native-authority evidence.

## Measured isolated builds

Python 3.12.14 and uv 0.12.19 executed all four packages. Each owned lock resolves the already measured Ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, setuptools 84.0.0 and wheel 0.48.0 candidates. Build-system pins match the installed locked build group. The new locks resolved offline using the existing public-PyPI artifact cache. This demonstrates neither an operating mirror nor a complete offline distribution kit.

For each package, only its 11 explicitly listed authored source/configuration files were copied into a fresh directory. A new development environment installed the lock with `--locked --offline --group build --no-managed-python --no-editable`. Ruff lint/format, strict mypy and all ten installed-command tests passed. Those tests cover the package identity, bounded liveness, unavailable readiness, invalid arguments, installed command/module agreement, inert imports and absence of other Python service/worker modules in that environment.

A wheel was built offline using the installed locked build backend. Its inspected members contain only five owned module files and that distribution's metadata; no runtime `Requires-Dist` exists. A fresh runtime environment installed the wheel with `--offline --no-index --no-deps`, and its distribution inventory contained only the expected package. The copied source and entire development environment were then removed. From outside the checkout, with `PYTHONPATH` unset and Python `-I`, checks confirmed the import came from the runtime environment, liveness and unavailable readiness returned their exact expected payloads, unsupported overrides failed, the installed command matched the module, and all four other service/worker modules were absent.

Across the four packages, **40 tests and 72 recorded commands passed their expected outcomes**: 64 commands exited 0, four readiness checks intentionally exited 1, and four unsupported override checks intentionally exited 2. Each report retains 11 explicit checks in addition to the commands. This evidence covers separate package installation, not network or database isolation.

## Retained evidence

Each report binds its 11 exact source files, command arguments, expected and actual exits, stdout/stderr byte counts and SHA-256 values. Complete wheel bytes are preserved losslessly as base64 in the adjacent `wheel-envelope.json`, with wheel members, byte count and digest. All 44 source bindings, 144 command-log hashes and four complete wheel envelopes were verified after execution. Git source and artifact revisions are recorded by the canonical [delivery evidence register](delivery-register.yaml); the immutable content hashes below identify the measured reports independently of publication order.

| Package | Report | Report SHA-256 | Wheel bytes |
| --- | --- | --- | --- |
| Inventory | [Local report](../../services/inventory/verification/bootstrap-20261004/report.json) | `290245034641f3b6f411f62f5b30020a1a20b881d2dda895f60fa16a67be56be` | 4,592 |
| Lifecycle | [Local report](../../services/lifecycle/verification/bootstrap-20261004/report.json) | `45e169e446437bea9196cd1592a4fd420f0bb3068d6e00d35d29ecde6d232a64` | 4,606 |
| Inventory worker | [Local report](../../workers/inventory/verification/bootstrap-20261004/report.json) | `f42e76f37b2961149912e018198393eab274e23ed3f127d0632134713a3e9d3c` | 4,938 |
| Lifecycle worker | [Local report](../../workers/lifecycle/verification/bootstrap-20261004/report.json) | `356d355a38f1ed8cd1af9099e05e00ce4d4738eb72406e408397a6a72f072a5b` | 4,961 |

Package READMEs supply developer commands: [Inventory](../../services/inventory/README.md), [Lifecycle](../../services/lifecycle/README.md), [Inventory worker](../../workers/inventory/README.md), [Lifecycle worker](../../workers/lifecycle/README.md). Exact wheel SHA-256 values and executable command arguments are retained in each report. No byte-identical wheel claim is made between different build environments.

## Coverage and remaining work

This is E1 local source/package evidence for P01.01. It adds the remaining Python service package boundaries and both selected worker package boundaries. It does not complete G01.01 or G01, and the word worker here denotes an owned deployment/package boundary rather than a functioning task consumer. The local records make no container, hosted-CI, release-publication or native-platform qualification claim; those executions require their own records.

No inventory discovery or observation persistence, lifecycle admission or operation journal, Temporal workflow/activity, queue dispatch, provider adapter, tenant/actor authority, fencing or recovery behavior is implemented. No endpoint, credential or native resource is used. The absent Domain/Application code is not reported as having passed exercised import-layer checks. Repository boundary controls and the separate package build isolation checks apply to the source that actually exists.

Next P01 work connects these owned artifacts to actual image/CI evidence and the reviewed local integration topology. Dependency readiness must remain unavailable until the required running dependencies and their failure behavior exist. Product capabilities and authenticated worker protocols belong to their later implementation packages rather than this bootstrap diagnostic.
