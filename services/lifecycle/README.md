# Lifecycle bootstrap

This independently owned Python package contributes to P01.01. Lifecycle will own execution admission and durable operation coordination. No admission, journal, workflow, dispatch, native effect or recovery behavior is implemented. The intended responsibilities remain in the [Lifecycle service specification](../../docs/services/lifecycle.md).

`lifecycle-health liveness` exits 0 and reports only that its short-lived diagnostic process loaded, with `scope=process_bootstrap`. `lifecycle-health readiness` exits 1 with `service_dependencies_not_implemented`. Unsupported arguments exit 2 without a success payload. Native operations are absent. These diagnostics do not establish a running service, dependency readiness or a consuming worker.

## Ownership and structure

`src/lifecycle/bootstrap/` composes the command; `src/lifecycle/interfaces/` handles diagnostic input/output. Importing the root package has no composition side effects. Domain, Application and Infrastructure modules will be created with their actual implemented responsibilities under the [Python context convention](../../docs/architecture/context-code-structure.md#7-python-services-and-site-workers). No sibling-service source or shared business package is loaded. This service owns its manifest, lock and package artifact.

## Install, check and build

Use Python 3.12.14 and uv 0.12.19, the measured development candidates. From this directory, with `UV_PYTHON_DOWNLOADS=never` set:

```sh
uv sync --locked --group build --no-managed-python --no-editable
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv run --locked --no-sync mypy
uv run --locked --no-sync pytest -q
uv build --no-build-isolation --wheel
uv run --locked --no-sync lifecycle-health liveness
uv run --locked --no-sync lifecycle-health readiness
```

The last command intentionally exits 1. The owned `uv.lock` resolves exact Ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, setuptools 84.0.0 and wheel 0.48.0. Runtime dependencies are empty. The backend and wheel helper have matching exact pins in the build-system requirements and the locked build group. Build with `--no-build-isolation` after installing that group.

Install the wheel into an empty Python 3.12 environment using `uv pip install --python <environment-python> --no-index --no-deps <wheel-path>`, then run the installed command outside this checkout with `PYTHONPATH` unset. The [Python foundations report](../../docs/implementation/p01-python-foundations.md) records the four packages' isolated builds and runtime checks. Tests also verify that sibling Python service and worker modules are absent in the independent installed environment. This diagnostic package is not a live worker or an HTTP service.
