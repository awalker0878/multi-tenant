# Owned DNS withdrawal before IPAM retirement

This implements part of W11/W25 using the existing [NetBox/DNS handoff](netbox-dns.md).
It follows the [retirement strategy](../provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md)
and [ADR-0033](../../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md):
remove an obsolete live binding while keeping ownership tombstones and retained
data obligations. It does not delete VMs, disks, retained copies, keys or IPAM rows.

## Prerequisites and exact withdrawal scope

The service owner must accept withdrawal of application exposure and dependencies
before removing DNS. Retained-data, recovery and shared-service dependencies remain
independently accountable. A DNS update cannot prove that an edge closed, sessions
ended or copies remain recoverable.

Keep the original allocation request, confirmed IPAM receipt, registration job,
registration scope and shared ledger. The registration attempt must match these
inputs and its latest registration result must show authoritative success. If it
is held, first use `--action reconcile` with the original registration files and
new read authority. An unmanaged record or missing ledger cannot be adopted for
cleanup merely because it has a familiar name or address.

Prepare a separately accepted withdrawal job/scope with:

- the same tenant/resource, zone, server, port and TSIG key identity;
- a new canonical operation UUID, current validity and the retirement engineering reference;
- `previous_marker` equal to `provisioner.execution.dns_change.marker_value(original_registration_job)`;
- exactly the original record name/type, `before` equal to its complete original
  `after` value including TTL, and `after: null`;
- an allowed-record scope containing only the original value and an accepted TTL ceiling.

Both A and PTR are supported. DNS endpoint/key migration, record updates, altered
values, multiple aliases and tombstone release remain outside this path. NetBox
must remain active with the same confirmed native identity and revision throughout
DNS withdrawal. Changed ownership or revision requires service-owner reconciliation.

## Validate and execute

```sh
python -m provisioner.execution.netbox_dns --action withdraw \
  --allocation /private/operator/allocation.json \
  --confirmation /private/operator/confirmed.json \
  --registration-job /private/operator/dns-job.json \
  --registration-scope /private/operator/dns-scope.json \
  --job /private/operator/dns-withdraw-job.json \
  --scope /private/operator/dns-withdraw-scope.json
```

Without `--execute`, this validates private inputs without contacting either
service. The returned binding hash covers the allocation, confirmation, withdrawal
job/scope and `registration: {job, scope}` containing both original registration
inputs. The encoding is the same sorted, indented JSON plus newline described in
the [registration runbook](netbox-dns.md).

Issue `hosting-netbox-dns-authority/1` for `action: withdraw`, that exact binding,
the current change window and the private credential/trust hashes. Use independently
accepted custody; the tool does not authenticate a JSON author. Add the existing
authority, NetBox read-token, CA, TSIG, shared ledger and new output options plus
`--execute`. No write-capable NetBox token is needed for DNS withdrawal.

The adapter holds the allocation lock, reserves `withdrawal-attempt.json`, then
uses the existing one-zone DNS transaction with native prerequisites. IPAM is read
before DNS, immediately before UPDATE and after readback. Contact authority is
checked before each request. DNS deletes only the exact owned RRset and replaces
its group/name markers with the withdrawal generation; markers remain present.

The result is `AUTHORITATIVE_TOMBSTONE_OBSERVED` only after exact authoritative
absence **and** the expected ownership markers have been read, with matching IPAM
observations. A missing record alone is insufficient. All results retain
`activation_authorized: false` and `reusable: false`.

## Uncertain and interrupted operations

Failure leaves `DNS_WITHDRAWAL_HELD` or an incomplete durable attempt. Preserve the
registration files, withdrawal inputs, attempt and transaction journals. A changed
UUID, output path or repeated `withdraw` cannot provide another UPDATE allowance.
No automatic DNS rollback, recreate, compensation or tombstone removal is performed.

Issue new authority for `reconcile-withdrawal` and the same full input binding.
Use the original six files with `--action reconcile-withdrawal --execute`, the
shared ledger and a new receipt output. This only reads native IPAM/DNS, including
when the original withdrawal deadline has expired. It preserves the original
`withdrawal-transaction.json`; `withdrawal-reconciliation.json` records the latest
observation. Active/foreign data, missing markers, stale ownership or unavailable
readback keeps the hold. A successful reconciliation never permits another UPDATE.

## Retire the allocation after all managed DNS cleanup

Forward and reverse remain separate transactions. Withdraw and observe both, plus
every other DNS registration tracked under the allocation. Partial completion
does not roll back successful cleanup or permit IPAM retirement.

`netbox_ipam.py --action retire` now checks every `dns-*` ledger slot under the
allocation lock before contacting NetBox. Each must have an exact parent/withdrawal
binding and a successful native tombstone report. The DNS observation and its
completed receipt must fall within the current IPAM retirement authority window.
When that window changes, use a newly authorized `reconcile-withdrawal` for each
slot before retirement. The newest withdrawal reconciliation takes precedence:
a failed new read cannot fall back to an older successful transaction.

The existing external `cleanup_ref` is still required. It covers independently
accepted exposure/routes/enrollment cleanup, unmanaged DNS, required propagation,
and retained-copy/key obligations that this ledger cannot establish. No DNS slots
does not prove there are no external DNS dependencies. A missing/corrupt ledger
is a recovery hold, not permission to start with an empty replacement ledger.

Use the [DNS propagation observer](dns-propagation.md) on each completed withdrawal
to collect authenticated secondary/recursive evidence for that cleanup reference.
It preserves the original tombstone generation and never flushes caches or
releases ownership. Selected-view readback is not universal cache-expiry proof.

NetBox retirement conditionally changes the row to `deprecated`; it does not
delete or release it. If that PATCH has an uncertain response, use the existing
IPAM `reconcile` action. Do not repeat the write, remove DNS attempts or reactivate
the allocation. Address/name reuse then requires the
[declared reuse quarantine and release](netbox-ipam.md) over complete dependency
evidence; a tombstone is never released or deleted by this withdrawal.

## Qualification limits

The shared lock only coordinates participating tools using the same durable
ledger. Current readbacks do not fence external writers or create a cross-service
atomic transaction. Qualify actual service RBAC, conditional writes, DNS marker
ACLs, protected transport, distributed durability and failure recovery at the site.

Loopback tests exercise real TLS/TSIG, exact A/PTR withdrawal, conflicts, missing
parents, lost replies, failed durable writes, partial forward/reverse cleanup,
stale and substituted receipts, and lost IPAM retirement responses. These are
implementation tests, not installed-service, native HA/security/recovery acceptance.
