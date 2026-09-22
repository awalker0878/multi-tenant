# Service-owner boundary

A service binding is a **declared handoff**: the provisioner states which reviewed
endpoint a workload security domain must use. It never provisions the service,
never registers the address itself and never claims the service is healthy.

Modules: `provisioner/services/`, `provisioner/allocations/{dns,ipam}.py`
Model: `provisioner/services/bindings.py`
Format: `hosting-service-binding/1`

## Binding resolution

For each service in the fixed order `dns`, `ntp`, `identity`, `logging`, `backup`:

1. take the resolved service profile from the request
2. read the profile's required `binding_class` from the service catalog
3. look up the reviewed endpoint for that service **at the selected site**
4. refuse if the endpoint is absent (`SERVICE_UNAVAILABLE`)
5. refuse if the binding class does not match (`SERVICE_UNAVAILABLE` with the
   required and available classes)
6. run the per-service validator over the endpoint fields
7. record the binding as `DECLARED_HANDOFF_NOT_VERIFIED`

Because the class must match, a service profile and a site endpoint cannot be
combined freely: `logging/standard` declares `logging-standard`, so a site that
only publishes `logging-protected` refuses the request rather than silently
downgrading.

## Per-service obligations

| Service | Required endpoint fields | The owner that still acts |
| --- | --- | --- |
| `dns` | `resolvers`, `zone` | resolver writer publishes the A records |
| `ntp` | time sources | time owner confirms reachability |
| `identity` | directory endpoints | directory owner confirms the consumer binding |
| `logging` | collector endpoints | logging owner confirms retention |
| `backup` | repository endpoints | backup owner confirms retention and restore |

Each declaration carries a `limits` list that names the remaining owner obligation,
and the delivery plan enumerates the corresponding `shared-service-handoff` and
`backup-retention` operations with their owners.

## DNS registration intent

`provisioner/allocations/dns.py` derives the records the owner must publish, one
per zone-qualified member, as `<tenant>-<wsd>-<domain>.<zone>` `A <address>`. The
registration state is `DECLARED_NOT_WRITTEN`: the resolver write is external and
its confirmation is external.

## Address allocation

`provisioner/allocations/ipam.py` allocates each zone prefix from the reviewed pool
and derives the offset gateway. An exhausted pool is
`PREFIX_POOL_EXHAUSTED`; an overlapping prefix or address is `ADDRESS_CONFLICT`.
Neither the prefix nor the gateway is ever substituted to make a request succeed.

## What this boundary does not do

It does not write to DNS, NTP, the directory, the log collector or the backup
repository. It does not hold credentials for any of them. It does not treat an
owner's silence as acceptance: an absent endpoint is a refusal.