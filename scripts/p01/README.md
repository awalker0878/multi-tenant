# P01 package verification

`run_quality.py` copies only the selected component into a new directory outside
the repository. It never installs into the checked-out service. Dependency caches,
earlier verification artifacts, generated output and sibling component source are
excluded. Each invocation requires a new output directory and retains the actual
source hashes, command arguments, exit codes, bounded timeouts, separate stdout and
stderr bytes, artifact hashes and failure details under `evidence/`.

```sh
python scripts/p01/run_quality.py \
  --workspace "$PWD" --output /tmp/p01-planning-measurement --component planning
python scripts/p01/run_quality.py \
  --workspace "$PWD" --output /tmp/p01-governance-measurement --component governance
python -m unittest discover -s scripts/p01 -p 'test_*.py' -v
```

The candidate record pins the already measured interpreter and package-tool
versions. Python components require their own committed lock, run Ruff, mypy and
their tests and build one owned wheel. The runner exports the owned production
lock with hashes, installs that complete closure into an empty runtime using
`uv pip sync --require-hashes --only-binary :all:`, then installs only the owned
wheel without dependency resolution. `uv pip check` and an independent exact
lock inventory comparison reject missing or unexpected distributions, including
development/build tools. The installed module must resolve inside that runtime.
The retained `production-requirements.txt` binds the hashes used for installation.

The three services own pinned Uvicorn and Psycopg binary dependencies and install
an additional `<service>-serve` entrypoint for private ASGI dependency diagnostics.
The runner launches that installed entrypoint on loopback with a disposable token
file and no database settings, retains the real HTTP responses, and verifies live
200, service-ready 503, anonymous dependency 401 and authenticated dependency 503.
It stops the server and removes the synthetic token after the checks.
The default CLI still measures process bootstrap, rejects readiness and refuses
unsupported input. Both workers retain a single stdlib distribution and one-shot
CLI behavior; installing the service runtime never adds task consumption.
`python_lock.py` recognizes only the current Linux/CPython string-platform marker
forms and selected dependency extras. Unknown marker semantics, forked package
versions or non-PyPI sources fail closed and need an explicit verifier update.

The unified package workflow covers Planning alongside every registered owner.
It replaces the redundant Planning-only workflow, whose zero-dependency assertion
was specific to the earlier bootstrap package.

PHP candidates now use committed `php_dependency_mode: replay`. All four private
Composer locks were resolved and retained during the initial candidate run, then
successfully replayed in package run 37239193553. Replay refuses a missing lock
and rejects lock changes; it never silently switches to dependency resolution.
A manual workflow request can explicitly select resolution for a later reviewed
candidate update. The [package evidence record](../../docs/implementation/p01-laravel-foundations.md)
retains the initial failures, corrected resolution and successful locked replay.

The PHP path checks the measured runtime, Composer, strict manifest/lock validity,
platform requirements, installed version/reference equality after clean install,
Pint, Larastan, Deptrac, Pest, boundary canaries, and cached configuration/routes.
The validation command uses `--no-check-all` solely because exact direct version
constraints are deliberate in this candidate. Composer's
[documented option](https://getcomposer.org/doc/03-cli.md#validate) suppresses overly
strict or unbounded constraint advisories; lock checking and other strict
validation remain enabled.

A bounded loopback Laravel process must serve liveness HTTP 200 and dependency
readiness HTTP 503 with the expected bodies and cache headers. The Console also
replays its npm lock, checks frontend boundaries and types, builds assets, and
executes Chromium against the real Laravel process. Any browser reports or traces
are retained as lossless base64 envelopes. Synthetic test settings and the
loopback-only cookie setting are supplied exclusively inside the copied fixture.
The application process is stopped on success or failure. This is development
package/application evidence, not a production web-server, native platform,
identity integration, service-dependency or security qualification.

`select_components.py` selects changed private components; Inventory/Lifecycle
service changes also select their registered worker because the architecture
permits owner-source inclusion. Shared build scripts, workflows, architecture and
runtime and contract inputs select every candidate. Unrecognized product/shared-package paths
and unavailable Git comparisons conservatively select every candidate. Docs-only
changes do not require a package build. Rename detection is disabled when reading
the NUL-delimited Git diff so both removed and added paths influence selection.
Ten selection tests cover private isolation, owner dependencies, renames/deletions,
shared input changes, prefix collisions, and invalid paths.

The workflow has read-only repository permissions and immutable action references.
Each selected matrix job uploads evidence even if verification fails. Installing
dependencies is allowed only in this connected development CI scope. No native
platform credentials, endpoints, provisioning or migration effects are involved.

The stable `Foundation checks` aggregate runs for every branch push and pull
request, including documentation-only changes. It rejects failed, cancelled or
missing selected jobs and invalid selection output. A family may be skipped only
when its selected component list is empty. The selector compares changed paths
between revisions against the current candidate/owner mapping; it does not claim
a versioned consumer graph across both revisions. Contract changes therefore
select all registered candidates conservatively.
