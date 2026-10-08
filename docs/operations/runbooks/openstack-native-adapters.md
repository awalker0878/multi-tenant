# OpenStack native API adapters

Scope: P07.02/P07.05 component execution and independent readback. Native admission,
commissioning and acceptance follow the [P07 input runbook](openstack-commissioning.md)
and [native workflow control](native-workflow-control.md).

## Protected inputs

`NativeBinding` binds tenant/site/project/application, job/operation/attempt,
campaign/executor/epoch, approved plan digest, canonical operation-plan digest,
ownership-map digest, custody UUID/generation and expiry. No caller may add a
command, URL or resource field outside the closed contract.

A protected runtime record contains exactly `operation_plan`, `writer` and
`observer`. The latter each contain `user_id` and four `endpoints`: `identity`,
`compute`, `network`, `volume`. Each endpoint contains `base_url`, pinned `address`,
`ca_file` and `token_file`. Paths are absolute protected files. All services in
one identity's set use the same project-scoped token. Writer and observer are
separate native identities; Keystone scope/user/expiry are independently checked.
For effect execution, both identity sets must use the same enrolled service URLs
and address pins, with distinct nonempty tokens. The worker rereads the runtime
record and credential separation before inspection and native requests; changing
the mounted runtime during an attempt requires reconciliation.
TLS verifies the commissioned hostname and CA while connecting to the pinned
address. Redirects, ambient credentials and caller-selected destinations are absent.

The operation plan has schema version 1, exact project/ownership/custody bindings,
API versions (`compute: 2.1`, `network: 2.0`, `volume: 3.0`) and ordered resources.
The currently implemented resource shapes are:

| Kind | Approved specification |
| --- | --- |
| port | Name, network, exact subnet/IP pairs, nonempty security groups, `admin_state_up=false`, `port_security_enabled=true` |
| volume | Name, size, volume type, availability zone and nullable image reference |
| server | Name, flavor, availability zone, config-drive, prior port keys and prior volume keys with exactly one boot volume |

Every disk and NIC belongs to exactly one server. Boot volumes require an image.
The worker derives tenant/resource/operation ownership metadata and maps only
journaled native IDs into subsequent requests. Unknown resource kinds/fields,
additional devices, duplicate ownership, changed bytes or unsupported API contracts
are rejected before native writes.

## Durable execution

`NativeApiEffect` resolves current Lifecycle authority before opening protected
runtime inputs. `NativeApiExecution` inspects the plan and commits a worker-owned
attempt/custody claim before effect submission. A single-use `before_api_sequence`
grant starts the sequence; every request and asynchronous poll checks
`during_api_sequence` authority and expiry.

The adapter journals `request_started` with payload digest before each POST,
then `request_accepted` with native ID and provider request ID. Ports are created
in quarantine, volumes are polled to available, and servers to ACTIVE within a
bounded deadline. A lost reply, cancellation, journal failure, expiration or
partial result holds the attempt. It never resubmits a create. Custody claims
survive restart and have no automatic expiry/delete path.

Credential rotation and expiry are checked after each current-authority callback
and through response completion. Declared response lengths must be satisfied;
conflicting length/chunk headers or an incomplete chunk stream remain unknown,
even when the received prefix parses as valid JSON. Retain the request-start
marker and reconcile with independent native evidence before any new authority.

`OpenStackReadback` uses the separate observer credential and accepted IDs. It
checks project/name/ownership, placement, exact server NIC and volume attachments,
boot image, flavor, config-drive and port quarantine/security/address fields.
A process return or ACTIVE status is not application readiness. Independent service,
data, backup and policy observations remain mandatory before activation.

## Read-only inspection

```sh
uv run --project workers/lifecycle --frozen lifecycle-native-inspect \
  --binding /protected/native-binding.json \
  --runtime /protected/native-runtime.json
```

Add `--observe --receipts /protected/native-receipts.json` for independent readback.
Receipts map approved resource keys to exact `{kind, id}` objects from the durable
journal. Missing/unknown IDs cannot prove absence or authorize retry. The command
always reports `native_write_authorized=false`; it has no write switch.

## Verification and native limits

Run `scripts/p07/qualify_native.py --output <directory>` with the pinned dependency
locks and a real PostgreSQL fixture configured by `P07_POSTGRES_BIN`. The campaign
requires zero skipped persistence tests, strict checks and package builds. HTTPS
peers are synthetic and establish E2 software evidence, not installed OpenStack
qualification. Native Q05/Q06, current owner/caller integrations, service/guest
adapters, provider stale-worker exclusion and retention/retirement require their
commissioned environment and independent observations.

The [P08 migration design](../../implementation/p08-native-migration.md) owns
VMware capture/export, copy-only conversion/transformation and delta migration.
Its export/import component is not P07 native provisioning acceptance evidence.
