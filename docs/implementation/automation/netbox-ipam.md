# NetBox address lifecycle

The [reference decision](reference-realization.md) selects the NetBox 4.7 REST
interface for exact IPv4 allocations. `tools/netbox_ipam.py` performs reserve,
confirm, read-only reconcile and retire operations. Retire changes the native
status to `deprecated`; it never deletes the record or makes an address reusable.
Address selection and compute-capacity approval precede this transaction.

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
JSON plus newline, as encoded by `tools.run_files.encoded`), exact `action`,
`valid_from`, `valid_until` (at most one hour), `change_ref`, `cleanup_ref`, and
`token_sha256`/`ca_sha256` of the exact private credential/trust files. The CA hash
is null when using system trust. `cleanup_ref` must identify separately accepted
dependent cleanup before `retire`. These records must come through the trusted
change system; the tool does not authenticate a JSON author.

```sh
python tools/netbox_ipam.py /private/operator/allocation.json --action reserve
python tools/netbox_ipam.py /private/operator/allocation.json --action reserve \
  --authority /private/operator/ipam-authority.json \
  --token-file /private/operator/netbox-token --ca-bundle /private/operator/ca.pem \
  --ledger /private/operator/ipam-ledger --output /private/operator/reserved.json \
  --execute
```

The first command is offline validation. For subsequent `confirm`, `reconcile`
or `retire`, issue authority for that exact action and use a fresh receipt path.
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

Sources: [REST authentication and conditional writes](https://netbox.readthedocs.io/en/stable/integrations/rest-api/),
[VRF uniqueness](https://netbox.readthedocs.io/en/stable/models/ipam/vrf/),
[4.7 release line](https://netbox.readthedocs.io/en/stable/release-notes/version-4.7/).
