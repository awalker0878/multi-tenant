# P00.03 candidate OCI image and extension results

Scope: P00.03/R01/R32/R34, supporting G00.03 and later G01 build controls. This record covers candidate image engineering for the existing synthetic compatibility fixtures. It does not select production images, approve network/mirror custody, implement product services, or change ADR-003's proposed disposition.

## Candidate decision and execution state

The [candidate manifest](../../spikes/compatibility/images/candidates.json) keeps the measured PHP 8.5.11, Python 3.12.14, Node 24.19.0, Composer 2.10.3 and uv 0.12.19 patches. The proposed family is Debian Bookworm on `linux/amd64`: PHP-FPM for the candidate PHP runtime, Python slim for Python, and Node slim used only during frontend building. Exact image availability and compatibility must be established by registry resolution and build results; a version string is not evidence of a completed build.

Execution state: source and bounded replay runner prepared; OCI execution has not yet been recorded in this document. Local Python compilation and shell syntax checks establish only source syntax. The remote run must resolve actual image digests, build the targets and retain its report before an image compatibility result is claimed.

The [image experiment instructions](../../spikes/compatibility/images/README.md) define resolution/replay commands and all target assertions. `images/run.py` defaults to replay and requires an existing lock; only explicit `--mode resolve` performs mutable-tag discovery. Derived builds and executions use digest identities. It records four rejection cases for mutable references, unexpected repositories, changed candidate inputs and platform drift.

## Build and extension bill of materials

| Item | Candidate and recorded identity | Responsibility proposed for acceptance |
| --- | --- | --- |
| PHP runtime | Docker Official Image PHP 8.5.11 FPM Bookworm; resolved upstream index/amd64 manifest, derived local configuration/layers, complete extension/OS package inventory | PHP platform owner with engineering/SRE |
| PHP extensions | Upstream Laravel-required core/XML/crypto/string/PDO extensions plus compiled `pdo_pgsql`; SQLite remains the synthetic transaction fixture; actual required list is executable in `candidates.json` | PHP context owners define needed extensions; platform owner maintains build |
| Python runtime | Docker Official Image Python 3.12.14 slim Bookworm; resolved base and derived identity, runtime-only locked dependency inventory | Python platform owner with context owners |
| Frontend build | Docker Official Image Node 24.19.0 Bookworm slim; exact npm version logged; existing npm lock/type/build, compiled assets copied to PHP runtime | Console/frontend owner |
| Dependency tools | Composer 2.10.3 and uv 0.12.19 copied from digest-resolved tool images into build/quality stages only | Delivery engineering |
| Added OS packages | Signed Debian snapshot fixed at `20261004T000000Z`; PHP extension headers/compilers removed from candidate runtime, PostgreSQL client library retained; complete installed versions captured | SRE/platform owner and security |
| Trust/distribution | Public registries and package endpoints for this connected experiment; candidate build is unpublished | Security and SRE must choose approved publishers, signature policy, mirrors and custody |

A loaded PostgreSQL extension is not PostgreSQL server qualification. The measured HTTP fixture runs Laravel through a bounded development server inside the non-root image; FPM configuration is checked separately. It does not establish production ingress, persistent sessions, database availability, TLS, HA or recovery behavior.

## Controls, evidence and interpretation

The intended execution retains the source revision, workflow/run identity, all input SHA-256 values, immutable base references, lock, command output/exit/timing, BuildKit metadata, image configuration identities and package inventories. The runtime targets must run as UID/GID 10001, deny source/root writes under read-only root, allow only explicit scratch directories, and omit test dependencies/tool binaries. Quality targets run without network access after the build and execute the existing positive/negative checks on the selected runtime base. HTTP must return the real HTML page and Inertia JSON, serve built assets, and reject a missing-CSRF mutation with 419.

Evidence of a build does not imply a trusted release: derived images are local, unpublished and unsigned. Base digest plus package lock and a signed fixed OS snapshot provides constrained build inputs; it does not prove byte-for-byte rebuild identity or archive every package distribution. The package inventory is a candidate BOM, not a claim of complete SPDX/CycloneDX generation or vulnerability-free operating-system packages.

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
