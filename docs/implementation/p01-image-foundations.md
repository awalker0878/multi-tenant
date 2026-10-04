# P01 Python image foundations

Package: P01.01. Gate criterion: G01.01, partial evidence. Execution date: 2026-10-04. Author/reviewer: Codex. [Hosted workflow run 37238148501](https://github.com/awalker0878/multi-tenant/actions/runs/37238148501) successfully built and exercised the three Python service bootstrap images and both selected Python worker bootstrap images at source `ba6acd71513c7d999cf51249d70d9c2be50967d9`.

This record covers Planning, Inventory, Lifecycle, Inventory workers and Lifecycle workers. It does not cover Laravel images: their image verification remains separate work. The existing [Planning package evidence](p01-planning-bootstrap.md) and [remaining Python package evidence](p01-python-foundations.md) establish the installed package behavior beneath these images.

## Source and build controls

Each matrix job verified the exact checkout revision and a clean status for its bound inputs before building. The source tree was `ede2dcc88635c8e446644bcd1e08f893c3925cc4`. Each image used 11 explicitly selected files from its owned component directory, copied into a temporary build context. The other services, workers, repository verification records and P00 spike source were absent from that context. The four shared runner/workflow/registry/lock files were separately bound as execution inputs, giving 15 source bindings per component.

The measured runner validated component identity, distribution/version, entrypoint, empty runtime dependencies, Python selection, the exact permitted context input set and immutable base references. Its source rejects missing or symlinked inputs, disallowed contexts and sibling/spike Dockerfile copies. During retrieval, the exact source revision's input validation was executed again for all five components. This is a successful-input replay; this image record does not claim a separate malformed-input canary campaign.

The multi-stage build installed only the locked build group, built the owned wheel offline using that installed backend, created a new virtual environment and installed the wheel with `--offline --no-index --no-deps`. The runtime stage copied that virtual environment onto the same pinned Python base. Build logs show setuptools 84.0.0 and wheel 0.48.0, with the locked transitive build dependency. Build-group installation can access its package index; the complete build is not claimed to run without network access or through an operating mirror.

| Input | Measured selection |
| --- | --- |
| Runner selection | GitHub-hosted `ubuntu-24.04`, `linux/amd64` |
| Docker client/server | 28.0.4 |
| Buildx | 0.37.1, commit `0b265a9f62db554fa9aba6dd19e1bd5704bc7d8a` |
| Container Python | 3.12.14 |
| Build uv image | 0.12.19, immutable child manifest selected in the input lock |
| Python child manifest | `docker.io/library/python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a` |
| uv child manifest | `ghcr.io/astral-sh/uv@sha256:d46db4c7b7f2e75ff80aeef95da4c2c6ff1ad399c13ab85067db4430b7c3b9c3` |
| Build output | Runner-local image loaded with `--load`; provenance generation explicitly disabled |

Base references are product-owned copies of the accepted P00 development selections; the image build does not load the spike lock at runtime. The source-bound lock in each raw report retains the original index digests and provenance. Docker/Buildx versions are observed runner tools, not separately pinned installers.

## Runtime observations

The copied build context was removed before runtime checks. Every image declared its owned diagnostic entrypoint, default `liveness` command, revision label and `USER 10001:10001`. Inspection confirmed Linux/amd64, no exposed service port and `HEALTHCHECK NONE`: these one-shot diagnostics cannot claim a continuously running service.

All diagnostic containers ran with a read-only root, no network, all capabilities dropped, `no-new-privileges`, 64-PID limit, 256 MiB memory limit and one CPU. They had no published ports or host-volume mounts. A separate in-container Python probe observed UID/GID 10001, zero effective capabilities, `NoNewPrivs=1`, a read-only root mount and only the loopback interface. The owned module loaded from `/opt/venv/lib/python3.12/site-packages/`; the isolated virtual environment's distribution inventory contained exactly its owned `0.1.0.dev0` package. `/build` and `/app/src` were absent. This is not a complete inventory or minimization assessment of every inherited base-image file.

For each component, liveness exited 0 with the exact `scope=process_bootstrap` payload. Readiness intentionally exited 1 with the service- or worker-specific `dependencies_not_implemented` reason. A `readiness --force` request exited 2 and emitted no success payload. All responses kept native operations disabled; both worker diagnostics kept task consumption disabled.

The five retained reports contain **50 commands: 40 successful exit-zero commands, five expected unavailable-readiness exits and five expected invalid-override exits**. There were no unexpected exits or timeouts. Actual container isolation values, complete commands and output bytes are retained alongside the reports.

## Image identities and retained reports

The identities below are runner-local image configuration digests, not published registry manifest digests. Image binaries were not exported into these evidence archives.

| Component | Image configuration digest | Image bytes | Raw report |
| --- | --- | --- | --- |
| Planning | `sha256:a142a20e5366fd1f5d9d266bbbffa5a747d984d21c9e52b946098e8c95acb7dd` | 124,376,376 | [Report](../../verification/p01/images/run-37238148501/planning/report.json) |
| Inventory | `sha256:3d768c3f42f40fbf289f882f490f34f396cf0ded85e8a48ff513578541e39cbd` | 124,376,442 | [Report](../../verification/p01/images/run-37238148501/inventory/report.json) |
| Lifecycle | `sha256:1429951f2c3d98874b753510338e5f0aed487504697618ea5c01170d7ba3fcb8` | 124,376,463 | [Report](../../verification/p01/images/run-37238148501/lifecycle/report.json) |
| Inventory workers | `sha256:4a19676e471c21d45ff773beb29ab749e808d72b9cdf5a46f9cbbe8b829cbd3b` | 124,377,077 | [Report](../../verification/p01/images/run-37238148501/inventory-workers/report.json) |
| Lifecycle workers | `sha256:3176fa6493a06e2ba18a4ea3009814f082375326003cf0f76d2b7cc2d12b3228` | 124,377,118 | [Report](../../verification/p01/images/run-37238148501/lifecycle-workers/report.json) |

The [retrieval index](../../verification/p01/images/run-37238148501/retrieval.json), SHA-256 `748d01cc160321c1cb409d34fbc417897559255493e2e061f85964fec8d2e1c3`, binds every report and its per-component retrieval record. It records the successful workflow identity, archive identities, source revision, image identities and totals. Raw reports were retained without rewriting their bytes.

Verification matched all five downloaded archive byte counts and SHA-256 values against GitHub artifact metadata, checked safe unique regular-file members before extraction, and verified all 100 stdout/stderr logs against recorded byte counts and hashes. All 75 reported source bindings, representing 59 unique files, were checked against exact immutable Git blob identities at the measured commit. Four shared files changed during the later PHP extension; their original bytes were fetched by exact commit rather than inferred from current workspace files. Each component's `retrieval.json` records the archive identity, actual verification checks, source blobs, raw-file digests and limits.

| Component | Raw report SHA-256 |
| --- | --- |
| Planning | `dcb588a52dda2441cdeff530c7a93c469bd510e0618b59f6a55263aeee910716` |
| Inventory | `601648204782894d8b19274f641ed8cd620e051f4ca357244e4987375d765149` |
| Lifecycle | `8e2c1427c483ed9f6d55b143386b1ed8f7d0621be92e524d46d7ce23ff3bf13f` |
| Inventory workers | `22b7d2c499d1eef30af404e39df508cf9be108d21a979b8105ad77f3e6099583` |
| Lifecycle workers | `286477669eb54958ab74747414448dbe6da71f981014627d8038142d1c71c022` |

## Completion boundary

These results establish five independently built and exercised Python development bootstrap images with the measured isolation restrictions. They do not establish persistent service availability, authenticated APIs, running worker consumption, database/broker/Temporal readiness, integration topology, tenant isolation, native platform behavior or G01 acceptance. Readiness correctly remains unavailable.

No image was pushed to a registry by this workflow. No signed image, release provenance attestation, SBOM, vulnerability assessment, complete inherited-package inventory, byte-identical rebuild or approved operating mirror is established. The retained artifacts preserve execution evidence and image configuration identities, not complete image-layer bytes. Laravel image results and the remaining P01 engineering/release controls require separate evidence before the gate can be assessed.
