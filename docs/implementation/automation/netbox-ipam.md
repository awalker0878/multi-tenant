# NetBox address lifecycle

The [reference decision](reference-realization.md) selects the NetBox 4.7 REST
interface for exact IPv4 allocations. `tools/netbox_ipam.py` performs reserve,
confirm, read-only reconcile, retire, quarantine and release operations. Retire
changes the native status to `deprecated`; it never deletes the record. Quarantine
declares the accepted reuse boundary over completed dependent cleanup, and release
observes that boundary elapsed. Neither action deletes, frees or reuses the native
row. Address selection and compute-capacity approval precede this transaction.

## Commission the service

Use the supported installed NetBox 4.7 patch release with TLS, per-tenant object
permissions and v2 tokens restricted to the runner's source and required objects.
Create text custom fields `hosting_owner`, `hosting_request`, `hosting_operation`
on `ipam.ipaddress`. Only the allocation service may modify these ownership fields.
The VRF and prefix must both belong to the exact tenant, and VRF `enforce_unique`
must be enabled. Separate WSD VRFs when their address spaces overlap.

Qualify the actual server's uniqueness enforcement, ETag/If-Match rejection and
token/object permissions before use. The adapter requires API-Version `4.7` and
an object ETag before any update. The local TLS tests exercise protocol handling
and failure behavior against synthetic responses; they do not qualify NetBox.
List and exact-detail reads must agree on native allocation identity and status;
malformed collection counts, IDs and unsupported allocation statuses stop use.

## Private request and execution

The `hosting-netbox-allocation/1` request contains `origin`, `scope` (environment,
site, platform, tenant, WSD keys), `member`, `operation_id`, positive `generation`,
native `tenant_id`, `vrf_id`, `prefix_id`, canonical IPv4 `prefix`, an exact
`address` including that prefix length, and `reservation_ref`. No free-address
search or automatic substitution occurs. The immutable request hash binds all of
these fields to the native object and the durable ledger.

The authority contains `request_sha256` (SHA-256 of sorted, two-space-indented
JSON plus newline, as encoded by `provisioner.execution.run_files.encoded`), exact `action`,
`valid_from`, `valid_until` (at most one hour), `change_ref`, `cleanup_ref`, and
`token_sha256`/`ca_sha256` of the exact private credential/trust files. The CA hash
is null when using system trust. `cleanup_ref` must identify separately accepted
dependent cleanup before `retire`; it is null for `reserve`, `confirm` and
`reconcile`. `evidence_sha256` binds the exact private reuse-quarantine declaration
for `quarantine` and `release`, and is null for every other action. These records
must come through the trusted change system; the tool does not authenticate a JSON
author.

The `hosting-netbox-release-evidence/1` declaration is a separate immutable private
file passed with `--release-evidence`. It contains `format`, `request_sha256` of
this exact allocation, an accepted `change_ref`, a bounded `duration_seconds`
(1 second to 365 days), `declared_at`, and `cleanup`. `cleanup` declares exactly the
six dependent categories `routes`, `dhcp_leases`, `dns`, `policy`,
`logging_attribution` and `incident_response`. Each category carries only `status`
(`NOT_STARTED`, `PENDING`, `COMPLETE`, `NOT_APPLICABLE`), an `evidence_ref` and an
`observed_at`. `NOT_STARTED` must claim neither. Quarantine requires every category
`COMPLETE` or `NOT_APPLICABLE`; `PENDING` cleanup cannot declare a reuse boundary.
Duplicate JSON keys, unknown categories, missing categories and unknown states stop
before NetBox contact.

```sh
python tools/netbox_ipam.py /private/operator/allocation.json --action reserve
python tools/netbox_ipam.py /private/operator/allocation.json --action reserve \
  --authority /private/operator/ipam-authority.json \
  --token-file /private/operator/netbox-token --ca-bundle /private/operator/ca.pem \
  --ledger /private/operator/ipam-ledger --output /private/operator/reserved.json \
  --execute
```

The first command is offline validation. For subsequent `confirm`, `reconcile`,
`retire`, `quarantine` or `release`, issue authority for that exact action and use
a fresh receipt path.
The ledger must be durable and shared by all allocation executors. File ownership,
0700 directories, 0600 records, nonblocking writer locks and write-ahead records
protect this execution path; service RBAC and uniqueness protect native ownership.
An interrupted or failed mutation leaves `OUTCOME_UNKNOWN`. Only observing its
intended completed outcome can clear that hold. Absence does not authorize retry.

A reserved address is unavailable to other requests. Confirm only after the
owning native resource and address binding have been established. Register DNS
through the [confirmed allocation DNS handoff](netbox-dns.md), which uses the
existing DNS client and current native IPAM reads under the shared allocation lock.
NetBox does not supply a timed compute lease: holds remain allocated
until explicit retirement and the service owner's later reuse procedure. No
automatic renewal/release timer fabricates capacity authority.

Retain the receipt with native IDs, scope, address, request digest and observed
revision. Current downstream checks still require independent platform/address
readback and the applicable reservation/IPAM handoff records.

Before `retire`, every DNS registration in this allocation's shared ledger must
have completed [owned withdrawal](netbox-dns-retirement.md), with matching native
tombstone observation and receipt inside the current retirement authority window.
A newer failed reconciliation overrides older success. Missing, uncertain, stale
or foreign cleanup stops before NetBox contact. Reobserve tombstones with newly
authorized read-only reconciliation when the retirement window changes. The
external `cleanup_ref` still covers the other accepted cleanup/retention duties;
the ledger does not discover unmanaged DNS or fence external writers.

## Reuse quarantine and release

`quarantine` and `release` are the two halves of one declared procedure. Both
require the exact private declaration and a fresh authority bound to it; both
require the address to be already `deprecated` in this ledger. The native row stays
`deprecated` throughout, is never deleted, and the tool never selects a free address.

`quarantine` re-checks every managed DNS tombstone, validates the declaration
against this exact allocation, and requires the declaration and every cleanup
observation to fall inside the current authority window. It then writes the
immutable `quarantine.json` record and replaces `head.json` with a terminal
`hosting-netbox-quarantine/1` receipt (`allocation_status` `QUARANTINED`,
`reusable` false, `reuse_not_before`). Repeating the same declaration is
idempotent; a different one is refused. Once declared, `retire` is refused.

`release` re-presents and re-validates the same declaration, requires the persisted
quarantine to bind it exactly, and requires the current time to have reached
`reuse_not_before`. The elapsed boundary is proved by the accepted declaration, not
by a timestamp recorded beside it, so editing the stored record cannot shorten the
quarantine. It writes `release.json` and a terminal `hosting-netbox-release/1`
receipt (`allocation_status` `RELEASED`, `reusable` true, `released_at`). Repeating
`release` returns the recorded `released_at`. A long quarantine is expected: the
release authority window is current, but the declaration is not required to be.

`reusable` is true only on the release receipt; quarantine and every earlier
receipt report false. The terminal receipt replaces the confirmed-allocation
receipt, so dependent DNS work fails closed and no later `register` can bind this
address. `reserve`, `confirm` and `retire` stay refused after release: reuse is a
new explicit allocation decision by the address authority, never an automatic
outcome of this tool. The release receipt carries `request_sha256`,
`quarantine_sha256`, `change_ref`, `reuse_not_before`, `released_at` and the
complete cleanup block for the change record.

```sh
python tools/netbox_ipam.py /private/operator/allocation.json --action quarantine \
  --release-evidence /private/operator/reuse-quarantine.json
python tools/netbox_ipam.py /private/operator/allocation.json --action quarantine \
  --release-evidence /private/operator/reuse-quarantine.json \
  --authority /private/operator/ipam-authority.json \
  --token-file /private/operator/netbox-token --ca-bundle /private/operator/ca.pem \
  --ledger /private/operator/ipam-ledger --output /private/operator/quarantined.json \
  --execute
```

Release uses the same inputs with `--action release` and a fresh receipt path once
the declared boundary has elapsed. This adapter records the decision and the
observed boundary; it does not perform the routes, DHCP, policy, logging,
incident-response or DNS cleanup it consumes as evidence.

Sources: [REST authentication and conditional writes](https://netbox.readthedocs.io/en/stable/integrations/rest-api/),
[VRF uniqueness](https://netbox.readthedocs.io/en/stable/models/ipam/vrf/),
[4.7 release line](https://netbox.readthedocs.io/en/stable/release-notes/version-4.7/).
