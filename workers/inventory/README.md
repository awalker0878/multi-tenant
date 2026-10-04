# Inventory worker bootstrap

This independently owned Python package contributes to P01.01. Inventory owns this package for future bounded, read-only collection. No endpoint is registered or contacted, and no collection runs. The intended responsibilities remain in the [Inventory service specification](../../docs/services/inventory.md).

`inventory-worker-health liveness` exits 0 and reports only that its short-lived diagnostic process loaded, with `scope=process_bootstrap`. `inventory-worker-health readiness` exits 1 with `worker_dependencies_not_implemented`. Unsupported arguments exit 2 without a success payload. Native operations are absent. These diagnostics do not establish a running service, dependency readiness or a consuming worker. Worker responses identify inventory as the owning service and declare `task_consumption_enabled=false`.

## Ownership and structure

`src/inventory_worker/bootstrap/` composes the command; `src/inventory_worker/interfaces/` handles diagnostic input/output. Importing the root package has no composition side effects. Domain, Application and Infrastructure modules will be created with their actual implemented responsibilities under the [Python context convention](../../docs/architecture/context-code-structure.md#7-python-services-and-site-workers). The architecture registry allows an explicit same-context owner artifact as a future build input, but this package currently has no dependency on the owner service package. It does not import an owner or sibling directory at runtime. It has no independent database or native authority.

## Install, check and build

Use Python 3.12.14 and uv 0.12.19, the measured development candidates. From this directory, with `UV_PYTHON_DOWNLOADS=never` set:

```sh
uv sync --locked --group build --no-managed-python --no-editable
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv run --locked --no-sync mypy
uv run --locked --no-sync pytest -q
uv build --no-build-isolation --wheel
uv run --locked --no-sync inventory-worker-health liveness
uv run --locked --no-sync inventory-worker-health readiness
```

The last command intentionally exits 1. The owned `uv.lock` resolves exact Ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, setuptools 84.0.0 and wheel 0.48.0. Runtime dependencies are empty. The backend and wheel helper have matching exact pins in the build-system requirements and the locked build group. Build with `--no-build-isolation` after installing that group.

Install the wheel into an empty Python 3.12 environment using `uv pip install --python <environment-python> --no-index --no-deps <wheel-path>`, then run the installed command outside this checkout with `PYTHONPATH` unset. The [Python foundations report](../../docs/implementation/p01-python-foundations.md) records the four packages' isolated builds and runtime checks. Tests also verify that sibling Python service and worker modules are absent in the independent installed environment. This diagnostic package is not a live worker or an HTTP service.
