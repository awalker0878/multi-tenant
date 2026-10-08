# P01 Laravel image verification and Console correction

Scope: P01.01, partial G01.01 evidence. Execution date: 2026-10-04. Author/examiner: Codex. All nine registered development images now have successful build and runtime-probe evidence. These results do not complete P01.01 or pass G01; service deployment and dependency integration remain separate work.

## Measured runs

The [nine-image run 37239193485](https://github.com/awalker0878/multi-tenant/actions/runs/37239193485) used source `4142571874a53b351a9c6023313185fe718d0dac`. All images built. Eight components passed their runtime checks, while Console failed its HTML request. The failed workflow and its raw report remain unchanged in the [retrieval index](../../verification/p01/images/run-37239193485/retrieval.json).

Console's server-side Inertia page check requires `resources/js/pages/Foundation.vue` even when Vite has compiled the browser assets. The runtime stage copied views and compiled assets but omitted that page directory, producing `ComponentNotFoundException` and HTTP 500. The corrective Dockerfile copies the owned page directory into the runtime image and keeps `ensure_pages_exist=true`.

The [Console-only corrective run 37239487917](https://github.com/awalker0878/multi-tenant/actions/runs/37239487917) at source `d0a7cefb23352ffc112638178bb225d20bf12368` passed its selected image job and `Foundation images` aggregate. It verified HTML status 200, the Foundation mount/descriptor, response protection headers, the Vite manifest and three built JavaScript/CSS assets. The [corrective retrieval index](../../verification/p01/images/run-37239487917/retrieval.json) and [raw report](../../verification/p01/images/run-37239487917/console/report.json) retain that distinct source and outcome. Later documentation-only workflow successes with skipped image matrices are not fresh image executions.

| Laravel component | Successful image configuration digest | Raw report |
| --- | --- | --- |
| Governance | `sha256:dfc3d97b2d2badbe264454422a4e5b136e6f7f89a606f8bac27112452b39a79c` | [Report](../../verification/p01/images/run-37239193485/governance/report.json) |
| Catalogue | `sha256:8096d07465a167aa32aab451c19a6b020f79acf3a85eb9f2301cd8addfb11e81` | [Report](../../verification/p01/images/run-37239193485/catalogue/report.json) |
| Assurance | `sha256:cfcd2aab161aac95198b902db3acb9a63ee587362cb43742715f981c819067a3` | [Report](../../verification/p01/images/run-37239193485/assurance/report.json) |
| Console | `sha256:501a19c0798e79f2c3105249975a4021eea064d3772ed2bcad15c4ebccc54727` | [Report](../../verification/p01/images/run-37239487917/console/report.json) |

The five Python service/worker image results are also retained in the nine-image index. Their diagnostic behavior follows the earlier [Python image foundation](p01-image-foundations.md).

## Build and runtime observations

The historical runs below used isolated owned contexts, private Composer locks, immutable PHP/Composer bases and a Debian package snapshot. Current P01 runtime images use the requalified Alpine inputs in the [remediation record](p01-image-remediation.md). Console additionally replays its npm lock with the pinned Node image and builds its frontend. Build logs bind actual dependencies; runtime probes observed PHP 8.5.11 and Laravel 13.34.0. The [build input lock](../../deploy/build/inputs.lock.json) records exact image references.

Successful PHP checks include FPM configuration validation, HTTP-kernel liveness 200 and intentionally unavailable readiness 503. Containers ran as UID/GID 10001 with a read-only root, loopback-only networking, zero effective capabilities and no-new-privileges. Writable application paths use bounded temporary mounts. The probes reject baked deployment configuration and leaked Composer, Node, tests or node_modules; retained output records PHP extensions, Composer runtime packages and operating-system packages.

The original nine-image run contains 85 commands and 170 command-log files, including the unexpected Console failure. The correction contains nine expected command outcomes and 18 logs. Recovery of the interrupted work rechecked archive byte counts/digests and log hashes. The corrective archive is 29,441 bytes with SHA-256 `762d8ae663e3605aa39c3af2276777c7e0ef3cb4e377156a18cc39eb57bdaed7`; all 40 corrective source bindings matched both SHA-256 and immutable Git blob identities. Its raw report SHA-256 is `0ecbfe0d51812ca8ec475682c194f2dcef35aca23672c3949752b8fef3002896`.

## Evidence boundary

These are runner-local image configuration digests, not published registry manifests. The records preserve logs, input identities and outcomes; image layers were not archived. FPM configuration and an in-process HTTP kernel do not establish a listening FastCGI deployment. Console browser hydration was separately measured by the [package suite](p01-laravel-foundations.md), not inside this image probe.

No operated installation, authenticated service identity, real dependency readiness, messaging, database isolation, backup/recovery, signed promotion, SBOM, vulnerability qualification or native platform behavior is established. Those requirements remain in P01.02–P01.06 and later native gates. Rebuild affected images after relevant source/input changes; keep original failures and subsequent corrections as separate immutable evidence.
