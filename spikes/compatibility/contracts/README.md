# Isolated P00 contract tooling experiment

This directory tests a synthetic OpenAPI contract and JSON Schema event envelope. The full [CI run 37232194144](https://github.com/awalker0878/multi-tenant/actions/runs/37232194144) passed against source [9843a0a](https://github.com/awalker0878/multi-tenant/commit/9843a0ab62452f8edcb0f5e19f25eb692ba3d723), including PHP 8.5.11 lint/model execution, after clean locked installs. It implements no product endpoint, domain behavior, broker or native operation. The current [contract conventions](../../../docs/contracts/README.md) and ADR-012 remain authoritative.

The exact generator, validation and client-runtime dependencies are in `uv.lock`; TypeScript and its compiler dependencies are in `package-lock.json`. The Python distribution embeds the OpenAPI Generator JAR. Its hash is recorded during each run. Java 17, Python 3.12, Node 24 and the optional PHP 8.5 runtime are observed separately in the report.

For a source-bound replay with recorded dependency-install logs, run the repository orchestrator with a new output directory:

```sh
python spikes/compatibility/run-contracts.py --workspace . --output /tmp/p00-contract-run
```

It requires PHP and records runtime versions, input hashes and bootstrap logs alongside probe evidence. The [retained complete CI result](../results/contracts/run-37232194144/evidence/report.json) records 18 wire fixtures, two invalid-schema controls, 53 deterministic generated files, Python/TypeScript checks and 11 PHP lint checks plus model behavior. Generated PHP/Python transport behavior is not claimed; the TypeScript HTTP call uses a mock.

For a manual probe from the repository root:

```sh
uv sync --locked --directory spikes/compatibility/contracts
npm ci --prefix spikes/compatibility/contracts --ignore-scripts --no-audit --no-fund
uv run --locked --directory spikes/compatibility/contracts python probe.py --results /tmp/p00-contract-evidence --require-php
```

Use a new, empty results directory for each execution. Omit `--require-php` only for a deliberately partial local run; its status is `LOCAL_PASS_PHP_NOT_RUN`. CI must require PHP. PHP needs `mbstring`; the generated-model test uses a private autoloader and does not require Composer or perform an HTTP request.

`probe.py` validates 18 request/response/problem/event cases, rejects two malformed schemas, generates PHP/Python/TypeScript clients twice, compares every generated file hash, detects a changed-schema output, compiles and executes Python/TypeScript probes, and runs generated PHP lint/model checks when PHP is available. The TypeScript transport uses an in-process mock with a synthetic token and reserved `.invalid` origin. It cannot contact a live service. Generated outputs live in temporary directories and are deleted at completion; their complete SHA256 inventory is retained. No generated package manifest is used to install floating dependencies.

The PHP namespace is `P00\Infrastructure\Generated`; Python uses the isolated `p00_private_client` package and TypeScript an isolated temporary client. Product consumers must import generated clients through their own Infrastructure adapters or the console's service-access boundary. Shared generated wire types must not replace domain models, authorize an operation, cross service databases or move business ownership.

The experiment intentionally records decoder weaknesses. A passing model/compile test does not replace schema validation at an untrusted boundary. See the [results and adoption limits](../../../docs/implementation/p00-contract-tooling-results.md) before selecting the candidate for P01.03.
