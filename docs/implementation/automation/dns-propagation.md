# Observe DNS propagation through selected views

`provisioner/execution/dns_propagation.py` extends the [owned DNS handoff](netbox-dns.md) with
read-only observations of the exact primary, required secondaries and recursive
views. Registration and [withdrawal](netbox-dns-retirement.md) use the same path.
The completed primary receipt, original job and original scope are immutable.
No UPDATE, cache flush, automatic discovery, tombstone removal or address release
is issued. A successful result is evidence for the service gate, not activation
authority or permission to reuse a name/address.

## Selected engineering profile

The initial internal DNS observation profile uses TCP with HMAC-SHA256 TSIG on
every query and response. Provision separate query-only keys where the DNS owner
supports them; do not give the observation account UPDATE rights. TSIG provides
message authentication, not confidentiality. The existing accepted internal
transport and view boundaries remain prerequisites.

Select one primary at the original update endpoint, at least one separately
addressed secondary and at least one separately addressed recursive view. Include
every required service endpoint/view explicitly; the tool cannot infer coverage
from successful queries or enumerate hidden anycast backends. Multiple views on
one IP need separately accepted ports/keys. The observer machine ID and network
namespace are fixed so a query from another network position cannot silently
stand in for the selected path. An external view acceptance reference establishes
which consumer population that source address/key represents.

Each view has an independently managed positive TXT control in the same exact
zone. Its name/value must identify the accepted view and must not be a record in
the change. The DNS owner provisions and protects these controls. They are read
before and after the owned records on each sweep; an unavailable/wrong view cannot
pass merely because the requested record is absent.

The [BIND configuration reference](https://bind9.readthedocs.io/en/v9.18.33/reference.html#address-match-lists)
describes key-based query/recursion access controls. Installed service versions,
view selection, permissions and protected transport still require qualification.

## Private input contract

The `hosting-dns-propagation/1` configuration contains exactly:

| Field | Meaning |
| --- | --- |
| `format` | `hosting-dns-propagation/1` |
| `job_sha256`, `scope_sha256`, `receipt_sha256` | `provisioner.execution.readback_core.digest` of the original job, scope and completed primary receipt |
| `observer_machine_id` | Exact lowercase 32-digit `/etc/machine-id` |
| `network_namespace_inode` | Positive integer inode of `/proc/self/ns/net` |
| `valid_from`, `valid_until` | Current timezone-aware observation window, at most one hour |
| `observation_ref` | Independently accepted observation/change reference |
| `max_seconds` | Overall query budget, integer 1–300 seconds |
| `targets` | Three to sixteen exact target objects |

Each target contains exactly `id`, `role` (`primary`, `secondary`, `recursive`),
`server` (canonical IP), `port`, `key_name` (absolute lower-case DNS name),
`tsig_sha256`, `view_ref`, `control_name` and `control_value`. The secret file is
a JSON map from every target ID to its base64 TSIG secret, with no extra keys.
`tsig_sha256` hashes the UTF-8 bytes of that base64 string, without a newline.
Credentials must decode to at least 32 bytes. All inputs and outputs are private
owner-only files outside the repository; real credentials are never committed.
Native execution refuses documentation/loopback addresses and test zones.

```sh
python -m provisioner.execution.dns_propagation \
  --config /private/operator/propagation.json \
  --job /private/operator/dns-job.json \
  --scope /private/operator/dns-scope.json \
  --receipt /private/operator/dns-result.json \
  --secrets /private/operator/observation-keys.json \
  --output /private/operator/propagation-result.json --execute
```

Without `--execute`, validation makes no network contact. Observation may inspect
an expired original write intent using a current observation window; this never
renews permission to write DNS. Failed reads can be repeated after the owner
resolves propagation or availability, using a new private output file.

## Observation and recovery behavior

Two complete sweeps read each target's positive control, exact zone SOA, CNAME
absence, group generation, name ownership markers and owned RRsets. Authorities
must return AA; recursive views must return RD/RA with AA clear. The selected
recursive endpoint must therefore be a resolver for this zone, not its local
authority. Each TCP exchange has a maximum five-second timeout and consumes the
common duration/current-authority budget.

Authoritative TTLs and values must match exactly. Recursive TTLs may have decayed
to zero but cannot exceed the original TTL; values and ownership generations
remain exact. Deleted records require an authenticated NXDOMAIN or NODATA answer
with the exact zone SOA. The negative-answer SOA requirement follows
[RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html#section-5). SERVFAIL, timeout,
unsigned responses, aliases, referrals without the exact negative SOA, unrelated
answers, stale data and missing/foreign markers hold the stage.

Success returns `SELECTED_DNS_VIEWS_OBSERVED_REQUIRES_ACCEPTANCE` with the input
digests and every timestamped observation. `activation_authorized` and `reusable`
remain false. These finite observations establish only the selected records and
views at those times. They do not prove that every cache expired, flush recursive
state, fence a concurrent writer or authorize reuse. Retirement still retains
the NetBox row and DNS tombstones and requires the independent cleanup reference.

The [delivery runner](delivery-runner.md) registers `dns_propagation`, with
parameter `dns_step` naming a direct completed `dns` dependency and files
`config`/`secrets`. Original allocation scope, job, scope and primary result come
from that dependency, so a caller cannot substitute an unrelated receipt. Place
this stage before the service or retirement acceptance gate, once for each
forward/reverse zone transaction.

A completed observation survives a coordinator crash without another query.
An interrupted read can safely repeat observation of the same generation; it
never replays UPDATE. If its contact window expired, publish
`<step-id>.recovery-authority.json` containing the original propagation config
with only `valid_from`, `valid_until` and `observation_ref` renewed. Targets,
observer position, keys, controls and original receipt binding cannot change.
Each selected configuration is retained by digest alongside the result.

## Verification boundary

The loopback tests use real signed TCP messages against independent authority
and recursive-answer fixtures. They cover decaying cache TTLs, stale/foreign
generations, negative SOA checks, unsigned replies, missing recursion, aliases,
service failure, changed controls, second-sweep reversion and saved-receipt
recovery without another network query. The fixtures do not implement real
secondary transfer or a recursive cache. Installed BIND/other DNS replication,
cache expiry, view configuration and workload-origin paths need actual native
service acceptance; the observer supplies the executable readback for that work.
