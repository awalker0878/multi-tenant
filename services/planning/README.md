# Planning

This independently owned Python service implements bounded P05 destination assessments, immutable plan compilation, current owner reads, review validity and confirmed facts. See the [P05 implementation](../../docs/implementation/p05-planning.md), [wire contract](../../contracts/openapi/planning-v1.json) and [operating runbook](../../docs/operations/runbooks/planning-review.md). Native execution remains unavailable; Lifecycle owns admission and reservation acquisition.

## Runtime and diagnostic boundaries

`planning-serve` starts Uvicorn on port 8080, binding `0.0.0.0` by default. Use `--host` and `--port` to select a listener. Its diagnostic ASGI interface retains these routes alongside the authenticated P05 API:

| Route | Access | Meaning |
| --- | --- | --- |
| `GET /health/live` | Unauthenticated | 200 means this HTTP process can answer; dependencies are not queried. |
| `GET /health/ready` | Unauthenticated | 503 `foundation_only`; this inherited probe does not certify P05 dependency or operational readiness. |
| `GET /health/dependencies` | Synthetic Bearer token | 200 requires the owned PostgreSQL connection and schema checks below. This is foundation readiness only. |

All responses disable caching. Unsupported methods return 405; unknown routes return 404. Authentication runs before dependency access. Missing/invalid credentials return 401; missing or malformed mounted authentication material returns 503. Dependency/configuration errors return a generic 503 without driver details, addresses or secret values. Unavailable responses carry `Retry-After: 10`. HTTP access logging and forwarded-header trust are disabled. The application does not implement workload operations or consume worker tasks.

The original `planning-health liveness` command still exits 0 for its own short-lived process only. `planning-health readiness` still exits 1 with `service_dependencies_not_implemented`; it cannot certify the persistent service. Unsupported command arguments exit 2. Root package imports perform no composition or network access.

## Synthetic configuration

Use a separate random health token and database role for each service. Configure only paths for secret values:

| Variable | Required value |
| --- | --- |
| `HEALTH_TOKEN_FILE` | Absolute mounted file path containing a printable ASCII token of at least 32 bytes |
| `DB_PASSWORD_FILE` | Absolute mounted file path containing the service-owned database password |
| `DB_HOST`, `DB_PORT` | PostgreSQL DNS name and TCP port; the name must match the server certificate |
| `DB_DATABASE`, `DB_USERNAME` | Owned database and least-privilege login role |
| `DB_SSLMODE` | Exactly `verify-full`; weaker modes fail closed |
| `DB_SSLROOTCERT` | Absolute mounted CA certificate path |

Both secret files are reread for each authenticated diagnostic request, so a rotated mounted file does not require process restart. Secrets are never accepted through plaintext password/token environment variables. This synthetic token authenticates fixture diagnostics only; it is not product user/service identity, tenancy or authorization.

The psycopg adapter makes a verified TLS connection, uses a two-second connection timeout and a two-second statement timeout, and marks the transaction read-only. An outer five-second deadline bounds the request's database work. It runs `SELECT 1`, then reads at most two rows from `app.foundation_schema`. Readiness requires exactly one row, supported integer version `1`, `current_user == DB_USERNAME`, and `current_database() == DB_DATABASE`. The request performs no migration or data write. Missing tables, wrong schema versions, bad credentials and TLS failures remain unavailable.

## Ownership and verification

`bootstrap/` wires the ASGI interface to the adapter. `interfaces/` owns HTTP and CLI adaptation, `application/` owns the typed diagnostic probe contract, and `infrastructure/` owns PostgreSQL access. Each context packages its own implementation and dependency lock under the [Python context convention](../../docs/architecture/context-code-structure.md#7-python-services-and-site-workers); no sibling-service source is imported.

Runtime dependencies are pinned to Uvicorn 0.53.0 and psycopg 3.3.6 with its binary implementation. `uv.lock` includes the resolved transitive closure and hashes from PyPI. The measured development interpreter is Python 3.12.14 with uv 0.12.19:

```sh
uv sync --locked --group build --no-managed-python --no-editable
uv run --locked --no-sync ruff check src tests
uv run --locked --no-sync ruff format --check src tests
uv run --locked --no-sync mypy
uv run --locked --no-sync pytest -q
uv build --no-build-isolation --wheel
uv run --locked --no-sync planning-serve --host 127.0.0.1 --port 8080
```

A clean production install must include the locked runtime dependencies, followed by the owned wheel. Installing only the wheel with `--no-deps` does not provide this HTTP runtime. The P01 package/image runners export production requirements from the committed lock and verify the installed closure.

Service-local tests cover authentication ordering, malformed/rotated secrets, read-only TLS settings, schema/identity rejection, generic database failures and a real installed persistent Uvicorn process. Mocked database tests do not establish real PostgreSQL or TLS availability. The P01.02 integration runner supplies that separate fixture evidence. The retained bootstrap verification directory records the earlier command-only baseline and is not evidence for this increment.
