# P00.03 candidate OCI image and extension results

Scope: P00.03/R01/R32/R34, supporting G00.03 and later G01 build controls. This record covers candidate image engineering for the existing synthetic compatibility fixtures. It does not select production images, approve network/mirror custody, implement product services, or change ADR-003's proposed disposition.

## Candidate decision and execution state

The [candidate manifest](../../spikes/compatibility/images/candidates.json) keeps the measured PHP 8.5.11, Python 3.12.14, Node 24.19.0, Composer 2.10.3 and uv 0.12.19 patches. The proposed family is Debian Bookworm on `linux/amd64`: PHP-FPM for the candidate PHP runtime, Python slim for Python, and Node slim used only during frontend building. The first connected OCI run resolved those exact tags to immutable platform manifests and successfully built and exercised all four targets.

Execution state: **PASS for the fixed-input candidate experiment**, run [37232132120](https://github.com/awalker0878/multi-tenant/actions/runs/37232132120), source `5052f8c0e7f27cb2bbc31cd59f1d992a096e738f`, observed 2026-10-04 20:27:06–20:28:51 UTC. All 49 recorded commands completed successfully on Linux/amd64 with Docker Engine 28.0.4 and Buildx 0.37.1. The [raw report](../../spikes/compatibility/results/images/run-37232132120/report.json) has SHA-256 `789b4e5ca3a4dde415aa39647462b2a8e521f46a5d616827cac3160e0c9a2191`.

The [retained input lock](../../spikes/compatibility/results/images/run-37232132120/inputs.lock.json) has SHA-256 `9298a430b975ab50d7cf4ccd89f627194bacc205682f61b92ad1f8f3db65d935`. The [retrieval record](../../spikes/compatibility/results/images/run-37232132120/retrieval.json) binds every retained file and records verified GitHub artifact ZIP SHA-256 `a450ef06beb077bdcd59cca372d74061a9f8894bf1f88d60dae4c4ccf0bb2665`. The observer is the GitHub Actions runner; Codex reviewed source/output consistency. No accountable operating owner has accepted this result as a production baseline.

The [image experiment instructions](../../spikes/compatibility/images/README.md) define resolution/replay commands and all target assertions. `images/run.py` defaults to replay and requires an existing lock; only explicit `--mode resolve` performs mutable-tag discovery. Derived builds and executions use digest identities. It records four rejection cases for mutable references, unexpected repositories, changed candidate inputs and platform drift.

## Separate committed-lock replay

Run [37232393563](https://github.com/awalker0878/multi-tenant/actions/runs/37232393563) at source `d988cfe5d09e32a22da93c9c1b4816878fe4c495` also **passed**, observed 2026-10-04 20:31:04–20:32:24 UTC. This execution used explicit replay mode: 39 commands succeeded, without the first run's ten tag/index-discovery commands. Its [raw report](../../spikes/compatibility/results/images/run-37232393563/report.json) records 94 input source bindings and has SHA-256 `e3764c8dc9cdbb1c43f820d2e88665a792c00a5d00bb570041984f20e4880db4`. The [retrieval record](../../spikes/compatibility/results/images/run-37232393563/retrieval.json) records verified artifact ZIP SHA-256 `69e53a1df720c8d64bfcc2f483bb6600769a0f0cca9d73371e359d477c7adb61`.

The input lock is byte-identical to the first run (`9298a430b975ab50d7cf4ccd89f627194bacc205682f61b92ad1f8f3db65d935`). All five pulled base image identities, all four OS/package inventories, and both PHP/Python runtime dependency and extension inventories matched. The replay repeated the quality, non-root/write-denial, HTML/Inertia/asset/CSRF checks successfully. All four newly built local image configuration digests changed, despite identical reported sizes; image byte equality is therefore not claimed, and the cause of the differing image identities was not isolated by this experiment.

| Replay target | Local image configuration digest |
| --- | --- |
| php-quality | `sha256:30c12f3543563cdffd45c11f769a1bcb36d037867a7c75e22610d50bb6d120a4` |
| php-runtime | `sha256:5dc973dd013e582ebd4b284cb6d460d341dbf17c4e104e052828222c38b82af5` |
| python-quality | `sha256:e84d6878933144441dc82f820179d8fe9465513c621678a3eed3cef80a4e88da` |
| python-runtime | `sha256:a6407b25c7698b8ba5d92648e4bdc6c653f570d0ba85dea8f8039079ae42a06c` |

The first-run identity table below remains the first observation. The replay records preserve their own BuildKit metadata, layer identities, command output and inventories; neither run overwrites the other.

## Build and extension bill of materials

| Item | Candidate and recorded identity | Responsibility proposed for acceptance |
| --- | --- | --- |
| PHP runtime | Docker Official Image PHP 8.5.11 FPM Bookworm; resolved upstream index/amd64 manifest, derived local configuration/layers, complete extension/OS package inventory | PHP platform owner with engineering/SRE |
| PHP extensions | Upstream Laravel-required core/XML/crypto/string/PDO extensions plus compiled `pdo_pgsql`; SQLite remains the synthetic transaction fixture; actual required list is executable in `candidates.json` | PHP context owners define needed extensions; platform owner maintains build |
| Python runtime | Docker Official Image Python 3.12.14 slim Bookworm; resolved base and derived identity, runtime-only locked dependency inventory | Python platform owner with context owners |
| Frontend build | Docker Official Image Node 24.19.0 Bookworm slim; exact npm version logged; existing npm lock/type/build, compiled assets copied to PHP runtime | Console/frontend owner |
| Dependency tools | Composer 2.10.3 and uv 0.12.19 copied from digest-resolved tool images into build/quality stages only | Delivery engineering |
| Added OS packages | Signed Debian snapshot fixed at `20261004T000000Z`; `libpq-dev` and compiler commands removed, PostgreSQL client library retained; inherited libc-related development headers remain visible in the inventory | SRE/platform owner and security |
| Trust/distribution | Public registries and package endpoints for this connected experiment; candidate build is unpublished | Security and SRE must choose approved publishers, signature policy, mirrors and custody |

A loaded PostgreSQL extension is not PostgreSQL server qualification. The measured HTTP fixture runs Laravel through a bounded development server inside the non-root image; FPM configuration is checked separately. It does not establish production ingress, persistent sessions, database availability, TLS, HA or recovery behavior.

## Controls, evidence and interpretation

The completed execution retains the source revision, workflow/run identity, all input SHA-256 values, immutable base references, lock, command output/exit/timing, BuildKit metadata, image configuration identities and package inventories. The runtime checks passed for UID/GID 10001, source/root-write rejection under read-only root, permitted scratch writes and absence of the enumerated test dependencies/tool binaries. Quality targets run without network access after the build and execute the existing positive/negative checks on the selected runtime base. The HTTP checks returned real HTML and Inertia JSON, served two built assets, and rejected a missing-CSRF mutation with 419.

Evidence of a build does not imply a trusted release: derived images are local, unpublished and unsigned. Base digest plus package lock and a signed fixed OS snapshot provides constrained build inputs; it does not prove byte-for-byte rebuild identity or archive every package distribution. The package inventory is a candidate BOM, not a claim of complete SPDX/CycloneDX generation or vulnerability-free operating-system packages.

## Measured input and output identities

These are the selected Linux/amd64 base manifest digests. The retained lock also records each source tag and upstream multi-platform index digest; the tags are discovery inputs only.

| Base | Immutable platform manifest digest |
| --- | --- |
| php | `sha256:c0dc98639fddeaad891a338e1e3fa2b2d724eb616bcd5a0bb1d8afd650e0fda3` |
| python | `sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a` |
| node | `sha256:e5a8dee7bc1e6a215d224a7ef8206f7e77271bc3cabd5febf2beafac0674f174` |
| composer | `sha256:bdd249749908be12facc9dec72e19704371bb893f96dff3e024ec89528a5a08d` |
| uv | `sha256:d46db4c7b7f2e75ff80aeef95da4c2c6ff1ad399c13ab85067db4430b7c3b9c3` |

The following local configuration identities describe the built targets from this run. They are not published registry artifact digests. Raw BuildKit metadata and layer identities remain in the evidence directory.

| Target | Local image configuration digest | Debian package entries | Docker reported size |
| --- | --- | --- | --- |
| php-quality | `sha256:ab5f1000574b74c5225e8f12361f44d8fad3c15ea77d5751262e6e6db59bbb02` | 137 | 804,235,815 bytes |
| php-runtime | `sha256:795f5d370a98d3be2d7d2c881b4403de74cbb67e1efb5842a1e77c3bde5f6064` | 126 | 552,643,619 bytes |
| python-quality | `sha256:8d169aaccb0a3df51bd051ba6830bf7463272540df14cea1890b1b24dcdcb6a6` | 105 | 425,617,464 bytes |
| python-runtime | `sha256:bc3b6b3f320c616ecfc80338452a13796e6b228a9c3bc7e879605e8b491c98d5` | 105 | 133,485,337 bytes |

All four inventories identify Debian GNU/Linux 12 Bookworm. [PHP runtime BOM](../../spikes/compatibility/results/images/run-37232132120/php-runtime-bom.json) and [Python runtime BOM](../../spikes/compatibility/results/images/run-37232132120/python-runtime-bom.json) enumerate the installed `dpkg` entries. [PHP runtime identity](../../spikes/compatibility/results/images/run-37232132120/php-runtime.json) records all 37 loaded extensions, PDO `sqlite`/`pgsql`, 75 versioned Composer entries and no development-marked Composer entries. [Python runtime identity](../../spikes/compatibility/results/images/run-37232132120/python-runtime.json) records the selected virtual environment's 11 runtime distributions, including Pydantic 2.13.5 and HTTPX 0.28.1. These inventories do not enumerate every file or bootstrap package inherited from upstream images.

## Observed checks and reviewed diagnostics

| Check | Actual result and retained evidence |
| --- | --- |
| PHP quality in candidate image | [Log](../../spikes/compatibility/results/images/run-37232132120/php-quality.log): PHP 8.5.11, Composer 2.10.3; Pint 31 files, Larastan no errors, Deptrac 0 violations/0 uncovered, Pest 20 tests/200 assertions, 14 intended negative controls passed. Debian Python 3.11.2 runs only the PHP canary harness; the application Python candidate remains 3.12.14. |
| Python quality in candidate image | [Log](../../spikes/compatibility/results/images/run-37232132120/python-quality.log): Python 3.12.14/uv 0.12.19; offline locked sync, Ruff, mypy over 26 files, four behavior tests, three import contracts and seven negative cases passed. |
| Frontend image build | [Build log](../../spikes/compatibility/results/images/run-37232132120/build-php-runtime.log): exact Node patch assertion, npm 11.17.0, clean npm lock installation, Vue type-check and Vite build passed. No npm upgrade was applied. |
| Runtime separation and filesystem controls | [PHP](../../spikes/compatibility/results/images/run-37232132120/php-runtime-negative-controls.log) and [Python](../../spikes/compatibility/results/images/run-37232132120/python-runtime-negative-controls.log): source/root writes denied, `/tmp` writes allowed; checked tool/test exclusions passed. PHP/Python identity records confirm UID 10001 and absence of selected development dependencies. |
| Image-lock controls | Raw report: all four invalid reference/repository/candidate/platform cases rejected by the lock validator. |
| Runtime HTTP and assets | Raw report: actual HTML and Inertia JSON requests passed, missing-CSRF POST returned 419, two compiled asset requests passed. The server log is empty; the assertions and command/run identities, rather than a fabricated request log, are the retained observation. |
| FPM configuration | [Log](../../spikes/compatibility/results/images/run-37232132120/php-fpm-configuration.log): non-root `php-fpm -t` succeeded. No FPM ingress traffic test was performed. |

BuildKit emitted `InvalidDefaultArgInFrom` warnings because Dockerfiles intentionally have no fallback base argument; the runner supplied all five validated immutable references. PHP extension compilation emitted terminal bold-sequence warnings in the non-interactive build. npm announced a newer major version without changing the installed one. PHP's expected invalid-transition cases logged domain exceptions while their 409/no-write assertions passed. None of these diagnostics was suppressed or counted as a successful negative control on its own.

The PHP runtime inventory still contains `libc6-dev`, `libcrypt-dev`, `libnsl-dev`, `libtirpc-dev` and `linux-libc-dev`, inherited through the selected base/package closure. `libpq5` is `15.19-0+deb12u1`; the `libpq-dev` build package and gcc/g++/make commands were removed. The images therefore separate application test dependencies but have not completed production image minimization. That assessment, full artifact SBOM/vulnerability review and FPM/ingress qualification remain explicit adoption work; this successful compatibility experiment does not establish them.

## Update and acceptance procedure

1. The accountable platform owner proposes a runtime/base/snapshot change with support and security reasons, affected contexts and rollback limits; console and Python/PHP owners assess their locks and required capabilities.
2. Delivery engineering explicitly resolves the reviewed candidate to new immutable references and runs the relevant image, dependency, HTTP and negative checks. A missing exact tag or failing command remains a failed experiment; no silent patch/family substitution is allowed.
3. Security/SRE review complete published artifact provenance, vulnerability findings, distribution trust, supported architectures, network/mirror closure and operating configuration. Owners decide the production candidate; this document does not supply their acceptance.
4. Record the accepted immutable image/configuration/release identities and actual reviewer in the environment BOM and canonical delivery register. Re-run affected qualification after input changes. Keep failed attempts and prior fixed-input results as historical evidence.

Actual owner names, production image family acceptance, registry trust/custody and mirror availability remain BL-P00-001 inputs. Engineering can prepare and measure candidates independently; no tooling pass closes G00 or authorizes native effects.

## Primary sources used for the candidate design

- [Docker build best practices](https://docs.docker.com/build/building/best-practices/) — multi-stage builds, minimal dependencies and digest pinning; consulted 2026-10-04.
- [Docker Official PHP image](https://hub.docker.com/_/php) and [upstream PHP Dockerfile](https://github.com/docker-library/php/blob/master/8.5/bookworm/fpm/Dockerfile) — extension build helpers and PHP-FPM base capabilities. The source was inspected at blob `fa4ef1edd06f304ee9aa48fb0669c5a61820c3bb`; actual base bytes are resolved by the experiment.
- [Docker Official Node image](https://hub.docker.com/_/node) and [Python image](https://hub.docker.com/_/python) — Debian variant characteristics; public tag lists do not substitute for measured exact-tag resolution.
- [uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/) and [locked synchronization](https://docs.astral.sh/uv/concepts/projects/sync/) — separate runtime/build dependencies, fixed tool images and locked environments.
- [Debian snapshot](https://snapshot.debian.org/) — fixed archive timestamps and historical package metadata. Production update cadence and archival trust still require owner decisions.
