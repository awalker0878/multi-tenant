# P00 candidate OCI build and runtime experiment

Scope: P00.03/R01/R32/R34. These images package the existing synthetic compatibility fixtures. They are not the seven product deployables, an accepted production baseline, or a native integration environment. [The image report](../../../docs/implementation/p00-image-results.md) owns measured outcomes and limits.

The first [recorded run](../results/images/run-37232132120/report.json), `37232132120` at source `5052f8c0e7f27cb2bbc31cd59f1d992a096e738f`, passed all 49 commands. It resolved five immutable base references, built four non-root targets, replayed the PHP/Python quality controls and exercised real runtime HTTP/asset/CSRF behavior. The retained input lock has SHA-256 `9298a430b975ab50d7cf4ccd89f627194bacc205682f61b92ad1f8f3db65d935`. The separate [committed-lock replay](../results/images/run-37232393563/report.json), run `37232393563` at source `d988cfe5d09e32a22da93c9c1b4816878fe4c495`, passed 39 commands with the byte-identical input lock. Base identities and OS/PHP/Python inventories matched; derived local image configuration digests differed. The experiment demonstrates successful replay of the selected inputs and checks, not byte-identical derived images. See the report for both runs' exact digests, inventories and diagnostics.

`candidates.json` fixes the runtime patches and Debian family to be investigated. Resolution selects each upstream `linux/amd64` child manifest and records both its digest and the upstream index identity. The runner builds exclusively with immutable image references; it never uses a candidate tag as an installed identity. An explicit resolution is needed when a reviewed candidate changes. Replay rejects altered candidates, unexpected repositories, mutable references and platform drift.

Run from a checkout with Docker, Buildx and Python 3:

```sh
python3 spikes/compatibility/images/run.py --workspace "$PWD" --output /tmp/p00-image-first --mode resolve
python3 spikes/compatibility/images/run.py --workspace "$PWD" --output /tmp/p00-image-replay --mode replay --lock /tmp/p00-image-first/evidence/inputs.lock.json
```

Each output directory must be new. The initial `evidence/inputs.lock.json` is the measured lock reviewed for `images/inputs.lock.json` after successful execution. Default replay reads that committed file; each replay retains a separate result. Resolution/build and the separate committed-lock replay both have retained results, with independent source and output identities. Candidate-resolution failure has no floating-tag or alternate-runtime fallback. The runner retains command output, failure status and source identities and removes its disposable containers in a `finally` block.

## Targets and assertions

| Target | Purpose | Boundaries exercised |
| --- | --- | --- |
| `php-quality` | Composer lock installation; PHP smoke, Pint, Larastan, Deptrac, Pest and existing negative canaries on the candidate PHP base | Runs as UID/GID 10001 without container capabilities or networking after dependencies are built; source is writable solely for intentional negative tests |
| `php-runtime` | Production Composer dependency selection, compiled Vue assets, PHP-FPM configuration and bounded actual HTTP | UID/GID 10001, read-only root, explicit disposable writable directories; rejects source/root writes and absent-CSRF request; no test tree, Composer, Node or Pest runtime dependency |
| `python-quality` | Locked Python environment; format/lint/types, behavior tests, import contracts, negative boundary cases and synthetic smoke | UID/GID 10001, no container capabilities/network during execution; offline locked sync cannot download missing dependencies |
| `python-runtime` | Runtime-only locked Python dependencies and smoke fixture | UID/GID 10001, read-only root with `/tmp` scratch; rejects source/root writes; no Ruff/mypy/pytest/Import Linter or uv |

The Node image is used only to type-check/build the existing frontend. The PHP fixture needs its existing `../frontend/resources/js/Pages` tree for the configured Inertia page-existence assertion; both PHP targets include those fixture pages. This layout is not a product service source layout.

The PHP image adds `pdo_pgsql` to the upstream PHP extension set. SQLite remains only the existing local transaction fixture. Finding `pgsql` in PDO's driver list verifies extension loading; it does not establish PostgreSQL server connectivity, TLS, pooling, migrations or concurrency. Those require the actual service/database tuple later.

PHP-FPM configuration is checked, but HTTP exercises the bounded `artisan serve` fixture transport inside the built runtime. It proves the container can execute the Laravel HTTP kernel and serve built assets. It does not qualify an ingress/FPM deployment, production session storage, CSRF policy for an operated domain, or managed-browser support. The already retained Chromium flow remains separate evidence; this experiment changes the image boundary and therefore replays the affected server behavior.

## Captured build inputs and remaining reproducibility limits

Base/index/platform image digests, candidate and source SHA-256 values, Composer/uv/npm locks, a fixed signed Debian snapshot timestamp, per-target BuildKit metadata, local derived image configuration digests/layers, OS/package inventories and PHP/Python dependency/runtime inventories are retained under `evidence/`. The Debian snapshot disables only expired `Valid-Until` checking; signatures and package hash checks remain enabled. This does not apply to live repositories.

The connected build uses public Docker Hub/GHCR, Debian snapshot, Packagist/GitHub, npm and PyPI. This is not an approved mirror, trust/custody or disconnected-installation result. Locked package versions/source references are not a claim that all upstream distribution bytes have independent archive hashes. No byte-for-byte reproducibility, signed release provenance, published image, OCI archive retention, full SBOM standard conformance or OS vulnerability qualification is asserted. The report distinguishes local image configuration identity from a published registry artifact digest.

Proposed update ownership is in the report. Any changed base digest, snapshot, extension, runtime patch, dependency lock, source or build instruction requires a reviewed new candidate result. Installed environment records must later reference published immutable artifacts and accepted release/configuration identities under the [configuration/BOM standard](../../../docs/operations/configuration-and-bom.md).

The measured PHP runtime retains inherited libc-related development headers, despite removal of `libpq-dev` and compiler commands. The candidate has not completed production minimization. Package inventories cover Debian packages, loaded PHP extensions/Composer entries and the selected Python virtual environment; they are not an exhaustive file-level image SBOM.
