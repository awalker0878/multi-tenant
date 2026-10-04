# Planning bootstrap

This independently owned Python package starts P01.01. It implements an installed diagnostic command and no assessment, profile interpretation, plan compilation, HTTP API, persistence or native integration. Planning's intended behavior remains in the [service specification](../../docs/services/planning.md).

`planning-health liveness` exits 0 and reports only that its short-lived process loaded. `planning-health readiness` exits 1 with `service_dependencies_not_implemented`. Unsupported arguments exit 2 without a success payload. Neither command establishes dependency readiness, service availability, authorization or a running server. Native operations are absent.

## Ownership and structure

`src/planning/bootstrap/` composes the command; `src/planning/interfaces/` adapts its input/output. The root import performs no composition. Domain, Application and Infrastructure modules will be created when they contain implemented behavior under the [Python context convention](../../docs/architecture/context-code-structure.md#7-python-services-and-site-workers). No sibling-service source or shared business package is loaded. The runtime uses only Python's standard library; this package owns its manifest and dependency lock.

## Install, check and build

The measured development interpreter is Python 3.12.14 with uv 0.12.19. Use an existing compatible interpreter; these commands disable automatic interpreter downloads. Run from this directory:

```sh
uv sync --locked --group build --no-managed-python --no-editable
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv run --locked --no-sync mypy
uv run --locked --no-sync pytest -q
uv build --no-build-isolation --wheel
uv run --locked --no-sync planning-health liveness
uv run --locked --no-sync planning-health readiness
```

The final command intentionally exits 1. Set `UV_PYTHON_DOWNLOADS=never` when running these commands. `uv.lock` pins the development and build dependencies; runtime dependencies are empty. The build backend and wheel helper are exact versions in both the build-system requirements and the `build` dependency group so `--no-build-isolation` uses the locked installed tools.

Install the resulting wheel into an empty Python 3.12 environment with `uv pip install --python <environment-python> --no-index --no-deps <wheel-path>`. Run the installed `planning-health` outside this checkout with `PYTHONPATH` unset. The [P01 bootstrap report](../../docs/implementation/p01-planning-bootstrap.md) records the actual isolated build and installation evidence, including its limits. No container image or independently running service has been built by this increment.
