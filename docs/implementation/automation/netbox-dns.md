# Confirmed NetBox allocation to authoritative DNS

The [reference profile](reference-realization.md) connects a confirmed IPv4
[NetBox allocation](netbox-ipam.md) to the existing [RFC 2136/TSIG writer](../../DNS_LIFECYCLE.md).
`provisioner/execution/netbox_dns.py` registers one initial A or PTR record in one accepted zone
and supports its [exact owned withdrawal](netbox-dns-retirement.md).
It checks native IPAM state and preserves a durable, write-once attempt. It does
not allocate addresses, confirm VM bindings, authorize activation or complete the
external IPAM/DNS evidence indexes.

## Private inputs and authority

Use the original `hosting-netbox-allocation/1` request, its confirmed
`hosting-netbox-receipt/1` receipt, and independently accepted DNS job/scope files.
Keep these and all credentials outside Git in owner-only files and directories.
Confirm the address only after independent native resource/address readback, as
required by the IPAM runbook. An operator-authored JSON receipt cannot supply that
evidence or authenticate its own approval.

The receipt must be `OBSERVED`/`active`, non-reusable, and bind the exact request,
scope, member, address, positive native ID and revision. The current allocation
ledger must retain that confirmation. A later IPAM read may refresh its observation
time; a changed identity, status or revision blocks DNS use.

For this adapter, the DNS job and scope use the allocation's `tenant_key` as
`tenant_id`. Set `resource_id` to `ipam-` plus the first 48 hexadecimal characters
of `provisioner.allocations.netbox_ipam.refs(allocation)['hosting_owner']`. That owner hash covers
the full environment/site/platform/tenant/WSD scope and member. It is deterministic
ownership metadata, not a credential or grant of authority.

The job must contain exactly one initial record, `previous_marker: null` and
`before: null`. For A, its only value is the confirmed IPv4 address without the
prefix length. For PTR, its owner name is that exact address's reverse name and
its one target is the independently assigned FQDN. The scope allows only the
selected value and accepted TTL ceiling. Updates, AAAA, multiple aliases,
adoption and reuse remain outside this interface. Deletion uses the separate
withdrawal action with the exact original registration and retained markers.

```sh
python -m provisioner.execution.netbox_dns --action register \
  --allocation /private/operator/allocation.json \
  --confirmation /private/operator/confirmed.json \
  --job /private/operator/dns-job.json --scope /private/operator/dns-scope.json
```

This command makes no service contact. It returns `VALIDATED_NO_CONTACT` and
`binding_sha256`: SHA-256 of `provisioner.execution.run_files.encoded` applied to an object with
`allocation`, `confirmation`, `job` and `scope` containing those exact four parsed
inputs. This is distinct from the DNS writer's compact JSON hashes.

The trusted change system supplies `hosting-netbox-dns-authority/1` with exactly:

- `format`, `binding_sha256` and `action` (`register`, `reconcile`, `withdraw` or `reconcile-withdrawal`);
- `valid_from` and `valid_until`, a current timezone-aware window of at most one hour;
- `change_ref`, the external accepted change reference;
- `token_sha256`, `ca_sha256` and `tsig_sha256`, hashes of the exact private files.

`ca_sha256` is null for system trust. The token file holds a scoped NetBox v2 token;
the TSIG file holds the base64 secret for the accepted DNS key. Use read-only
NetBox access for this handoff. DNS server ACLs must cover only the selected record
and the writer's exact ownership-marker names. These JSON bindings rely on trusted
custody; they do not verify an approver's signature.

After independent approval, append these options to the validation command:

```sh
  --authority /private/operator/dns-authority.json \
  --token-file /private/operator/netbox-read-token \
  --ca-bundle /private/operator/ca.pem --tsig-file /private/operator/dns-tsig \
  --ledger /private/operator/ipam-ledger --output /private/operator/dns-receipt.json \
  --execute
```

Use the same durable, shared ledger as `netbox_ipam.py`. An output path is only a
receipt destination; choosing a new output does not create another write allowance.

## Execution and recovery

The adapter holds the allocation's nonblocking writer lock throughout the handoff.
It checks the exact tenant/prefix/unique VRF and list/detail allocation identity,
active status and receipt ETag before DNS observation, immediately before UPDATE,
and after DNS readback. Both transports check current contact authority before
each request. The existing DNS client retains authenticated authoritative reads,
server-side ownership prerequisites and its one-UPDATE limit.

An immutable attempt is reserved before contact under the allocation's zone/owner
slot. Changing the DNS UUID, endpoint, key, name, TTL or output path cannot bypass
that slot. Even an early failure leaves the registration attempt held. Preserve
`attempt.json` and `transaction.json`; do not remove them to force a retry.

For recovery, keep all four original inputs unchanged, issue new authority for
`action: reconcile`, and run with `--action reconcile --execute` and a new output.
This reads native IPAM and DNS only. The new read authority may inspect an expired
original DNS write intent. It cannot renew write permission or send UPDATE. The
original transaction journal remains intact; `reconciliation.json` holds the most
recent readback. Absence, conflict, changed IPAM or unavailable readback keeps the
hold. A successful readback also does not enable another registration attempt.

`AUTHORITATIVE_REGISTRATION_OBSERVED` means the exact generation and record were
observed while the allocation remained confirmed across the sampled reads.
`DNS_REGISTRATION_HELD` requires operator reconciliation. If IPAM changes after
a DNS update, the retained DNS report may show success while the overall handoff
remains held. There is no automatic rollback of the DNS record.

## Commissioning boundaries

Run forward and reverse jobs independently with their own scopes, keys and receipts.
Verify both describe the same accepted name/address before downstream use. Forward
success does not compensate for reverse failure. Independently verify any required
recursive and secondary observations and export accepted opaque evidence through
the [DNS registration handoff](../../engineering/authoritative-dns-registration-handoff.md).

The shared lock serializes participating allocation tools. It is not a distributed
fence against administrators, direct service writers, another ledger or server-side
changes between reads. Actual NetBox uniqueness/ETags, service RBAC, DNS ACLs,
transport protection and durable storage must be commissioned. Neither service
provides a cross-service atomic transaction here. The [retirement handoff](netbox-dns-retirement.md)
now gates IPAM deprecation on current managed DNS tombstones, and address reuse now
requires a [declared quarantine and observed release](netbox-ipam.md) over complete
dependent cleanup; complete cross-service retirement, tombstone release, IPv6 IPAM
integration and the DNS *name* reuse quarantine remain open.

Loopback tests use real TLS and TSIG bytes with synthetic NetBox/DNS authorities.
They cover A/PTR handoff, current-state races, expiry, lock exclusion, durable
failure and lost-reply reconciliation. They do not qualify installed services,
live HA, security containment or recovery. No acceptance index is populated.
