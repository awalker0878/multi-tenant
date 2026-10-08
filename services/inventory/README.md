# Inventory service

This independently owned Python service implements P04 read-only enrollment, durable discovery, observation history, matching proposals and confirmed fact delivery alongside the original P01 diagnostics. Native write operations and formal platform qualification remain unavailable. Intended context behavior remains in the [service specification](../../docs/services/inventory.md).

## Runtime and diagnostic boundaries

`inventory-serve` starts Uvicorn on port 8080, binding `0.0.0.0` by default. Use `--host` and `--port` to select a listener. Its foundation diagnostics expose these routes:

| Route | Access | Meaning |
| --- | --- | --- |
| `GET /health/live` | Unauthenticated | 200 means this HTTP process can answer; dependencies are not queried. |
| `GET /health/ready` | Unauthenticated | 503 `foundation_only`; this diagnostic does not certify enrolled-site or native readiness. |
| `GET /health/dependencies` | Synthetic Bearer token | 200 requires the owned PostgreSQL connection and schema checks below. This is foundation readiness only. |

All responses disable caching. Unsupported methods return 405; unknown routes return 404. Authentication runs before dependency access. Missing/invalid credentials return 401; missing or malformed mounted authentication material returns 503. Dependency/configuration errors return a generic 503 without driver details, addresses or secret values. Unavailable responses carry `Retry-After: 10`. HTTP access logging and forwarded-header trust are disabled. The separate Inventory API and worker lease interface are defined in `contracts/openapi/inventory-v1.3.json` and the P04 runbook.

The original `inventory-health liveness` command still exits 0 for its own short-lived process only. `inventory-health readiness` still exits 1 with `service_dependencies_not_implemented`; it cannot certify the persistent service. Unsupported command arguments exit 2. Root package imports perform no composition or network access.

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

Runtime dependencies are pinned to Uvicorn 0.53.0, psycopg 3.3.6 with its binary implementation, and pika 1.4.4. `uv.lock` includes the resolved transitive closure and hashes from PyPI. The measured development interpreter is Python 3.12.14 with uv 0.12.19:

```sh
uv sync --locked --group build --no-managed-python --no-editable
uv run --locked --no-sync ruff check src tests
uv run --locked --no-sync ruff format --check src tests
uv run --locked --no-sync mypy
uv run --locked --no-sync pytest -q
uv build --no-build-isolation --wheel
uv run --locked --no-sync inventory-serve --host 127.0.0.1 --port 8080
```

A clean production install must include the locked runtime dependencies, followed by the owned wheel. Installing only the wheel with `--no-deps` does not provide this HTTP runtime. The P01 package/image runners export production requirements from the committed lock and verify the installed closure.

Service-local tests cover authentication ordering, malformed/rotated secrets, read-only TLS settings, schema/identity rejection, generic database failures and a real installed persistent Uvicorn process. Mocked database tests do not establish real PostgreSQL or TLS availability. The P01.02 integration runner supplies that separate fixture evidence. The retained bootstrap verification directory records the earlier command-only baseline and is not evidence for this increment.

## Discovery operations

See [P04 implementation](../../docs/implementation/p04-inventory.md) and [the operation runbook](../../docs/operations/runbooks/inventory-discovery.md) for explicit supported bounds, independent enrollment inputs, controlled migrations and live evidence. `inventory-publish --limit 100` drains at most 100 confirmed immutable facts.

Enrollment policies are returned in stable policy-ID order, at most 50 per page.
Follow `next_cursor` to retrieve subsequent policies within the same tenant, site
and owner scope.

## Migration profile roles

VMware, OpenStack and AHV can each supply source workload observations or destination
capability observations. Enrolled platform identity is checked at profile intake;
native disk identities, NICs and controllers must remain unambiguous. AHV's observed
installed versions are included in the exact source tuple binding.

Configuration review uses source workload profiles for VMware/AHV source endpoints,
without requiring destination-resource permissions. Only selected endpoints require
freshness at configuration confirmation; operation readiness separately requires the
source for migration and the destination for provisioning and other native tasks.
Cold export uses image transfer and independent image verification accounts for all
three destination platforms. It does not require a delta protocol.

Common destination routing lives in `domain/migration.py`; AHV and VMware validation
remain in their platform modules. Discovery and administrator confirmation never
establish native qualification or execution authority.

VMware destination discovery restricts import placement to the `VIRTUAL_MACHINE`
folder hierarchy returned by the [vCenter folder API](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/folder/get/).
Host, network, datastore and datacenter folders cannot be selected for VM import.
