# Build the offline execution runtime

`tools/runtime_build.py` builds the repository-pinned Python dependency set and
Terraform executable from accepted local artifacts. It supplies a concrete
rebuild path for W02/W04 and the [owner installer](owner-installation.md),
[guest execution](native-guests.md) and [delivery runner](delivery-runner.md).
It does not install the operating system, download dependencies, create accounts,
issue credentials or contact a native platform.

## Accepted foundation and artifacts

Use the independently recoverable Ubuntu 24.04 Linux amd64 bootstrap host. The
base CPython must already be installed from the accepted artifact source and
match the repository minor version in `config/toolchain.json`. Select its exact
patch version and executable digest. The executable and resolved ancestors must
be controlled by root or the current custodian, without group/other write access.
The base operating-system image digest and runtime acceptance reference cover
its standard library, shared libraries and OS dependencies; the builder does not
attest that image or independently establish this trust. It rejects a base
interpreter that is itself a virtual environment.

Privately stage only accepted wheels and the Linux amd64 Terraform ZIP. Do not
supply source distributions, dependency URLs or arbitrary build scripts. Every
wheel, including pip and all transitive dependencies, has an exact distribution
name, version, filename and SHA256. The set must include every pin reachable from
`requirements-repository.txt`. Repository pins alone are not a complete artifact
approval. Retain the approved complete manifest and artifacts in independently
recoverable custody, including their source/signature review.

## Private request

A `hosting-runtime-build/1` JSON object has exactly these fields:

| Field | Required value |
| --- | --- |
| `format`, `enabled` | `hosting-runtime-build/1`; explicit boolean, true only after acceptance |
| `source_commit` | Accepted full source SHA; the executing checkout must match it exactly |
| `python`, `python_sha256`, `python_version` | Absolute installed base interpreter path, its SHA256 and exact `3.13.x` version |
| `base_os_sha256`, `base_runtime_ref` | Accepted OS image SHA256 and independent base runtime acceptance record |
| `artifact_acceptance_ref` | Acceptance record for the complete wheel and Terraform artifact set |
| `wheels` | One to 64 objects, each with canonical lowercase distribution `name`, exact `version`, absolute local `.whl` `path`, and `sha256` |
| `terraform` | Object with absolute ZIP `path`, archive `sha256`, extracted `binary_sha256`, and repository-pinned `version` |
| `output` | New absolute directory outside the source, under a private existing parent; never an input artifact directory |

Paths use simple absolute names without shell metacharacters. Inputs and their
request/authority files are private, owned by the current custodian, without
symlink traversal. Duplicate packages, unsafe archive members, symlinks in
archives, unexpected Terraform entries and oversized archives are rejected.
Wheel metadata must match the manifest. Wheels are accepted executable software;
checking their metadata and hashes does not substitute for provenance review.

The separate `hosting-runtime-build-authority/1` object has exactly `format`,
`config_sha256`, `valid_from`, `valid_until` and `change_ref`. The digest is
`provisioner.execution.readback_core.digest(config)`. The timezone-aware interval is current and
at most one hour. No repository template grants this authority.

```sh
python tools/runtime_build.py --config /private/runtime/build.json
python tools/runtime_build.py --config /private/runtime/build.json \
  --authority /private/runtime/authority.json --execute
python tools/runtime_build.py --config /private/runtime/build.json --verify
```

The default command validates the request without executing an artifact. Explicit
execution verifies the source, base host and artifacts, creates the venv at its
final location with copied interpreters and without bundled pip, and bootstraps
pip from its accepted wheel. It installs only direct local wheel paths with
hash checking, no index, no dependencies resolved by pip, no source builds and
no cache. A fixed environment sets `PIP_CONFIG_FILE=/dev/null`, disabling all pip
configuration files; ambient pip, proxy and Python settings are not inherited.
The actual `pip check` and complete installed-distribution comparison reject
missing/conflicting dependencies and unexpected packages. Terraform's extracted
bytes, reported version and platform must all match.

Runtime subprocesses use a private umask. Before initial completion, the builder
removes group/other permissions from its newly created regular files and
directories, including executable modes copied from the accepted base. It never
repairs permissions on an already completed runtime.

The builder compiles and seals ordinary hash-checked Python bytecode alongside
all installed files, modes and directories. Only the venv's internal `lib64`
alias is permitted. Normal imports preserve this seal; custom optimized Python
modes are outside this profile. OS/base-runtime changes require a new accepted
build. Python documents that [venvs must be rebuilt at their final location](https://docs.python.org/3.13/library/venv.html);
pip documents [configuration disabling](https://pip.pypa.io/en/stable/topics/configuration/)
and [hash-checked wheel installation](https://pip.pypa.io/en/stable/topics/secure-installs/).

## Retention, use and recovery

A completed destination contains `env/bin/python`, `env/bin/ansible-playbook`,
`bin/terraform`, retained artifacts, exact requirements, original intent and
`receipt.json`. The completion records the source, base interpreter observations,
complete installed distribution map and file seal. Use those exact executable
paths in accepted guest/worker/Terraform requests and retain the receipt digest
as their runtime acceptance evidence. Keep operating jobs, logs, provider caches,
plans, state, credentials and owner journals outside this runtime directory.
The custodian must keep the runtime accessible only to its accepted execution
account. A shared non-root worker requires a separately accepted installation
and access handoff; making a private build publicly accessible is not automated.

The output directory is created atomically, and a writer lock serializes access.
An incomplete destination remains held, including after a lost command response
or controller crash. The tool never reinstalls into it, deletes it or copies
partial files into another runtime. Retain the failed evidence and build from
the same approved inputs at a new destination under a new exact authority.
There is no native platform effect to roll back at this stage.

An exact completed repeat verifies every retained file without executing the
runtime again. `--verify` performs that observation without fresh build authority
or the original staged artifacts. Changed, extra, missing or writable files are
held, never repaired in place. The original base executable and source must
still match. Local hashes cannot detect coordinated rollback of the entire
runtime and receipt; retain independent custody and the accepted receipt digest.
Do not replace a running worker's source/interpreter or clear its native holds
when upgrading a runtime.

## Execution evidence

Focused regressions exercise artifact substitution, isolation, interruption,
concurrent access, retained-byte changes and exact reuse. The hosted
`lab/run_runtime_build_lab.py` acquires disposable candidate wheels, creates a
fixture archive around the actual pinned Terraform binary, and then executes
the actual venv/pip/compile/version commands in an empty network namespace.
It verifies a complete build, normal imports, missing transitive dependency
failure, held incomplete reuse and altered-runtime rejection. Candidate hashes
and hosted base custody are explicitly synthetic acceptance inputs, not a
production image approval. No installed platform is qualified by this test.
