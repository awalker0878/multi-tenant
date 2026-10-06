# Lifecycle simulation worker

This independently owned Python package contributes to P01.01. Lifecycle owns this package for future explicitly scoped execution. P06 supplies the separately owned PostgreSQL simulation effect store, sealed readback and grant redemption. The Temporal orchestrator lives in the Lifecycle service; no native effect is implemented. The intended responsibilities remain in the [Lifecycle service specification](../../docs/services/lifecycle.md).

`lifecycle-worker-health liveness` exits 0 and reports only that its short-lived diagnostic process loaded, with `scope=process_bootstrap`. `lifecycle-worker-health readiness` exits 1 with `worker_dependencies_not_implemented`. Unsupported arguments exit 2 without a success payload. Native operations are absent. These diagnostics do not establish a running service, dependency readiness or a consuming worker. Worker responses identify lifecycle as the owning service and declare `task_consumption_enabled=false`.

## Ownership and structure

`src/lifecycle_worker/bootstrap/` composes the command; `src/lifecycle_worker/interfaces/` handles diagnostic input/output. Importing the root package has no composition side effects. Application and Infrastructure modules implement simulated effect ownership under the [Python context convention](../../docs/architecture/context-code-structure.md#7-python-services-and-site-workers). The architecture registry allows an explicit same-context owner artifact as a future build input, but this package currently has no dependency on the owner service package. It does not import an owner or sibling directory at runtime. It owns the simulation database and has no native authority.

## Install, check and build

Use Python 3.12.14 and uv 0.12.19, the measured development candidates. From this directory, with `UV_PYTHON_DOWNLOADS=never` set:

```sh
uv sync --locked --group build --no-managed-python --no-editable
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv run --locked --no-sync mypy
uv run --locked --no-sync pytest -q
uv build --no-build-isolation --wheel
uv run --locked --no-sync lifecycle-worker-health liveness
uv run --locked --no-sync lifecycle-worker-health readiness
```

The last command intentionally exits 1. The owned `uv.lock` resolves exact Ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, setuptools 84.0.0 and wheel 0.48.0. Runtime dependencies are empty. The backend and wheel helper have matching exact pins in the build-system requirements and the locked build group. Build with `--no-build-isolation` after installing that group.

Install the wheel into an empty Python 3.12 environment using `uv pip install --python <environment-python> --no-index --no-deps <wheel-path>`, then run the installed command outside this checkout with `PYTHONPATH` unset. The [Python foundations report](../../docs/implementation/p01-python-foundations.md) records the four packages' isolated builds and runtime checks. Tests also verify that sibling Python service and worker modules are absent in the independent installed environment. The diagnostic command does not start the separate P06 simulator. Install its complete hash-locked runtime requirements before installing the owned wheel, as the Dockerfile does.

## Isolated effect owner

`lifecycle-simulator` exposes distinct authenticated effect, reconciliation and
read-only observation routes over verified TLS. It redeems each short-lived grant
with Lifecycle before accepting a simulated effect. Reconciliation seals absence
against late arrivals. The Console cannot call these routes. Apply the worker-owned
SQL migration as `simulation_owner`; runtime receives only its explicit grants.
The default image diagnostic remains non-consuming. See the
[simulation runbook](../../docs/operations/runbooks/durable-simulation.md).
