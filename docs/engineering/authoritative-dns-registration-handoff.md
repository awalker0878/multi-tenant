# Authoritative DNS registration handoff

**Purpose:** bind DNS registration lifecycle evidence to a confirmed authoritative IPAM allocation without making this repository an IPAM or DNS authority.

The existing `tools/dns_change.py` remains the separately scoped RFC 2136/TSIG mutation mechanism. This package does not invoke it. It only validates exported DNS lifecycle evidence and decides whether an immutable registration intent is ready to be handed to the DNS owner.

## Source boundary

The architecture requires authoritative IPAM to reserve and confirm addresses before dependent name registration. DNS forward/reverse records, TTLs and reuse conditions are part of the same lifecycle, while recursive resolution, authoritative hosting, dynamic update and transfer/replication duties remain separate. Service failure must pause changes rather than create guessed addresses, alternate names or broader update authority.

The repository therefore keeps actual DNS names and A/AAAA/PTR values outside Git. Only opaque name-assignment, zone-scope, IPAM-allocation and authoritative-system references are retained here.

## Active evidence index

The active index is `sources/capabilities/dns_registration_index.json` and is intentionally empty today.

A future registration record must bind:

- immutable registration and operation identities plus generation;
- reservation/request/WSD scope;
- one authoritative IPAM allocation ID;
- an opaque name-assignment reference;
- A, AAAA and/or PTR record types, but never literal values;
- opaque forward/reverse zone-scope references;
- TTL-policy reference;
- required observation classes;
- authoritative DNS system record/version;
- lifecycle chronology and owners;
- evidence/source references.

One registration binds one confirmed IPAM family. A and AAAA therefore use separate registrations when dual-stack allocations are independently authoritative.

## Observation semantics

`AUTHORITATIVE` readback is always required for REGISTERED state. `RECURSIVE` and `SECONDARY` observations are required only when the approved service profile declares them. This preserves the source distinction between an authoritative write/readback and actual resolver/secondary convergence.

Each observation is one of COMPLETE, PENDING, FAILED, UNKNOWN or NOT_APPLICABLE. A required observation must be COMPLETE before the record may be REGISTERED. Authoritative success alone cannot silently prove recursive or secondary propagation.

## Lifecycle

Supported exported states are REGISTERED, RELEASE_PENDING, TOMBSTONED, RELEASED and UNCERTAIN.

Retirement preserves the DNS owner marker/tombstone boundary until name/address reuse obligations are satisfied. A released name cannot precede its tombstone boundary. UNCERTAIN state blocks blind retry and requires authoritative discovery.

## Preflight

`scripts/check_dns_registration_preflight.py` accepts only opaque registration scope. It rejects caller-supplied FQDN or address fields because those values must come from the authoritative name/IPAM owners after handoff.

Ready state is:

`DNS_INTENT_READY_EXTERNAL_CHANGE_NOT_EXECUTED`

and means only that the DNS owner may resolve the approved exact name/allocation through its authoritative systems, construct an independently scoped `dns_change.py` job/scope, and follow the approved change process.

The preflight always keeps `may_write_dns`, `may_delete_dns`, `may_release_name`, `may_apply` and `may_activate` false.

## Current repository state

Because the active IPAM and DNS indexes contain no confirmed allocation/registration records, the repository example remains held:

```sh
python scripts/check_dns_registration_preflight.py examples/dns_registration_intent.json.example --expected-status HOLD_IPAM_ALLOCATION_NOT_CONFIRMED
```

Local wire tests continue to prove only the bounded RFC2136/TSIG implementation against the disposable loopback authority. They do not qualify BIND, Windows DNS, appliances, DNSSEC, recursion, secondary convergence or production ACLs.

[DNS lifecycle](../DNS_LIFECYCLE.md) · [Authoritative IPAM handoff](authoritative-ipam-allocation-handoff.md) · [Name/time/initialization services](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md)
