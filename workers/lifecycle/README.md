# Lifecycle worker

This independently owned Python package contributes to P01.01. Lifecycle owns explicitly scoped execution. P06 supplies the separately owned PostgreSQL simulation effect store, sealed readback and grant redemption. The Temporal orchestrator lives in the Lifecycle service. P07 adds native adapter components and read-only inspection; native product dispatch is not enabled. The intended responsibilities remain in the [Lifecycle service specification](../../docs/services/lifecycle.md).

`lifecycle-worker-health liveness` exits 0 and reports only that its short-lived diagnostic process loaded, with `scope=process_bootstrap`. `lifecycle-worker-health readiness` exits 1 with `worker_dependencies_not_implemented`. Unsupported arguments exit 2 without a success payload. Native dispatch is disabled. These diagnostics do not establish a running service, dependency readiness or a consuming worker. Worker responses identify lifecycle as the owning service and declare `task_consumption_enabled=false`.

P08 adds separately invoked `lifecycle-worker-native --config <protected-file>` and
`lifecycle-migration-accounts --config <protected-file>` commands. The first composes
the authenticated native effects server with its protected scoped registry; the
second performs read-only source/target account commissioning checks. Both are
declared in the owned image entrypoint registry. The default image entrypoint remains
the diagnostic command. See [commissioning](../../docs/implementation/p08-runtime-commissioning.md)
for configuration and the outstanding native owner/qualification requirements.

## Ownership and structure

`src/lifecycle_worker/bootstrap/` composes the command; `src/lifecycle_worker/interfaces/` handles diagnostic input/output. Importing the root package has no composition side effects. Application and Infrastructure modules implement simulated effect ownership under the [Python context convention](../../docs/architecture/context-code-structure.md#7-python-services-and-site-workers). The architecture registry allows an explicit same-context owner artifact as a future build input, but this package currently has no dependency on the owner service package. It does not import an owner or sibling directory at runtime. It owns the simulation database and has no native authority.

## Install, check and build

Use Python 3.12.14 and uv 0.12.19, the measured development candidates. From this directory, with `UV_PYTHON_DOWNLOADS=never` set:

```sh
uv sync --locked --group build --no-managed-python --no-editable
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
uv run --locked --no-sync mypy
uv run --locked --no-sync pytest -q
uv build --no-build-isolation --wheel
uv run --locked --no-sync lifecycle-worker-health liveness
uv run --locked --no-sync lifecycle-worker-health readiness
```

The last command intentionally exits 1. The owned `uv.lock` resolves exact Ruff 0.16.10, mypy 2.4.0, pytest 9.1.1, setuptools 84.0.0 and wheel 0.48.0. Runtime dependencies remain the locked psycopg and Uvicorn closure used by the simulator and read-only inspection. The backend and wheel helper have matching exact pins in the build-system requirements and the locked build group. Build with `--no-build-isolation` after installing that group.

Install the wheel into an empty Python 3.12 environment using `uv pip install --python <environment-python> --no-index --no-deps <wheel-path>`, then run the installed command outside this checkout with `PYTHONPATH` unset. The [Python foundations report](../../docs/implementation/p01-python-foundations.md) records the four packages' isolated builds and runtime checks. Tests also verify that sibling Python service and worker modules are absent in the independent installed environment. The diagnostic command does not start the separate P06 simulator. Install its complete hash-locked runtime requirements before installing the owned wheel, as the Dockerfile does.

## Isolated effect owner

`lifecycle-simulator` exposes distinct authenticated effect, reconciliation and
read-only observation routes over verified TLS. It redeems each short-lived grant
with Lifecycle before accepting a simulated effect. Reconciliation seals absence
against late arrivals. The Console cannot call these routes. Apply the worker-owned
SQL migration as `simulation_owner`; runtime receives only its explicit grants.
The default image diagnostic remains non-consuming. See the
[simulation runbook](../../docs/operations/runbooks/durable-simulation.md).

## P07 native adapter components

`lifecycle-native-inspect` validates a protected native operation plan and binding.
Optional `--observe --receipts` uses an independent OpenStack observer and exact
journaled native IDs. It grants no write or retry authority.

`NativeApiEffect` resolves protected runtime connections, redeems current Lifecycle
authority, and invokes the durable native API adapter. Each request is journaled
before submission; returned object/request IDs are retained; unknown outcomes
hold custody without automatic retry. The internal effect API trusts only its
independently composed caller resolver and never accepts caller identity or commands.

See [native adapter operations](../../docs/operations/runbooks/openstack-native-adapters.md)
for the exact plan, runtime and journal boundaries. P08 owns the separate
[VM migration architecture](../../docs/implementation/p08-native-migration.md).

## P09-A composed migrations

The protected registry composes source capture, retained archive, copy conversion
and destination import separately. `openstack_capture` reads a stopped Nova source
and captures every local/attached disk through Nova, isolated Cinder copies and
private Glance images. `ahv_capture` binds each stopped source disk to a Prism
image and durable accepted task. `vmware_capture` and `vmware_export_archive`
retain the isolated clone, NFC manifest and OVF descriptor. No Terraform provider
or VDDK is in this data path.

`native_image_archive` version 3 permits an explicit same-grant continuation for
OpenStack/AHV immutable image GETs. A private file lock excludes concurrent byte
writers; persisted capture identity, checksums, continuation count and the original
deadline survive a restart. Changed captures, expired grants, missing receipts and
uncertain native POST responses remain held. VMware supports bounded in-process
range continuation against a live NFC lease; a process restart cannot create a new
lease under an old operation. Independent AHV readback can reconstruct a missing
completed capture receipt from all retained accepted tasks; partial task inventory
and ambiguous custody cannot be repaired by replaying creates.

`migration_copy_conversion` version 4 accepts an exact sealed `guest_profile`:
`id`, `family`, `distribution`, `major_version`, `architecture`, `target_platform`,
`firmware`, `commands_sha256` and `artifact_sha256`. Conversion first creates
sector-verified private RAW copies, runs the pinned offline libguestfs profile,
re-inspects guest identity, retains before/after hashes and converts the prepared
disks to their explicit target format. Writable hard links and shared directories
are rejected. Destination import checks any prepared receipt's platform and
firmware against its own plan. Profiles in `guest-profiles/` are appliance build
inputs; seal the exact scripts, signed offline drivers/packages and toolchain in
the commissioned read-only rootfs. They require qualification for each advertised
guest tuple. An offline preparation receipt never establishes boot or application
health.

`vmware_destination` uses OVF `CreateImportSpec` and `ImportVApp`/NFC with native
`datacenter-*` and `vm-*` identities. Its independently read target ancestry,
datastore/network memberships, hardware profile, disconnected NICs and powered-off
state must match the selected scope. AHV and OpenStack imports use their native
image/storage/workload APIs. Source and destination platform roles can be composed
in all nine directions; that composition does not establish native qualification.

Account commissioning manifest version 3 requires explicit `platform` on both
`source` and `target`. Each side has separate `collector`, `writer` and `observer`
accounts and the following native scope:

| Platform | Side scope | Account fields |
| --- | --- | --- |
| VMware | `api_version`, `instance_uuid`, `session_manager`, `authorization_manager` | `user_name`, pinned `endpoint`, explicit required/forbidden `privileges` per native entity |
| OpenStack | `project_id` | `user_id`, `roles`, four pinned `endpoints` (`identity`, `compute`, `volume`, `network`) and `image` endpoint |
| AHV | `project_id`, `prism_central_id`, `cluster_id` | `user_id`, `key_id`, `credential_sha256`, `authorization_policies`, pinned `endpoint` |

All service endpoints for one OpenStack account must use one scoped credential;
all three roles must observe the same native origins. Principals and credentials
must be distinct and remain unchanged during probing. Version 1/2 manifests remain
supported. A successful commissioning probe verifies identity, connectivity and
scope; it does not establish mutation permissions or workload readiness.

`lifecycle-worker-observer --config <protected-file>` starts the separate TLS
observation process. Its configuration binds `callers_file`, `registry_file`,
`observer_id`, `tls_cert_file`, `tls_key_file` and `schema_version=1`. Exact plan,
stage, caller and phase assignments select fixed native service endpoints, subject
IDs and assertions. Guest, service, dataset, security and health outcomes need a
native measurement timestamp no older than the commissioned bound (at most five
minutes). Each allow/deny policy result needs its own measurement timestamp. A
fresh HTTP read cannot restamp a stale restore or traffic result as passed.

The authenticated `/internal/native-progress` route exposes only a current
redeemed `export_copy` grant's journaled verified disk count, bytes and archive
completion. These counters survive worker restarts and never invent percentage,
remaining time or in-flight bytes. Missing/stopped/expired authority returns a hold.
Apply native migration `005_any_to_any.sql` as the separate journal owner before
running these adapters; runtime remains append-only. Synthetic API/TLS peers are
E2 mechanism evidence, not E3 platform or E4 receiving-owner acceptance.
