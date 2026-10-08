# Contextual commissioning, bounded discovery and transfer continuation

Owners: Inventory and Console for readiness; Inventory worker for discovery;
Lifecycle worker for retained export. This increment advances P07/P08/P09/P10
engineering. Native campaigns and receiving gates retain their existing status.

## Operator workflow

**Site inventory → Operator readiness** now selects discovery, provisioning,
migration, adoption, operating handover or retirement. Migration also selects a
method. Inventory derives requirements from that selection and the enrolled
source/destination platforms. Cold export does not request a delta protocol;
AHV does not request separate Glance accounts. Other-task values remain saved
and can be displayed explicitly. This selection does not rewrite migration plans.

Each field includes an example, format and accountable owner. The summary counts
applicable inputs; zero outage/data-loss targets are supplied values. A reference
alone is **awaiting verification**. Signed owner observations can make a field
verified, failed or stale; unreadable or invalid evidence is unavailable. The
remaining-actions list explains the next step. Recheck evidence refreshes the
saved packet's observations; expiry also updates on the displayed page. A page
is an observation at its last refresh, not an execution authorization.

Inventory 1.6 adds `GET/POST /v1/tenants/{tenant}/sites/{site}/operator-readiness`.
Legacy operator-input paths and their response schemas stay intact. Context and
values share one immutable revision/digest, stale-write precondition and
idempotency receipt. The existing migration `007_operator_inputs.sql` suffices;
no table rewrite is needed. Deploy Inventory before the new Console client.
Every response/export retains `native_write_authorized: false`.

## Publishing original owner evidence

The [evidence contract](../../contracts/schemas/inventory/commissioning-evidence-v1.json)
defines an observation report, signed receipt and public-key registry. Reports
contain actual observations from the responsible system; the publisher does not
run a native check or derive a successful result from a reference string.

1. Save and download a contextual input packet. Run the selected owner's actual
   read-only/account, custody, recovery or service check and retain its original
   evidence bytes. The existing `lifecycle-migration-accounts --config …` command
   can produce account observations; it cannot prove guest/application support.
2. On the owner side, prepare an `observation` with producer ID, tenant/site,
   exact packet/configuration digests and one or more checks. A check binds its
   field, canonical saved-value SHA-256, explicit verified/failed result, observed
   and expiry times, protected evidence path and original byte SHA-256. Canonical
   JSON uses sorted keys, ASCII escaping and compact separators, as Inventory's
   `canonical` function does.
3. The independently enrolled producer signs with its raw 32-byte Ed25519 private
   key, readable only by its owner. For example, from `services/inventory`:

   ```sh
   uv run --locked inventory-readiness-receipt \
     --packet /protected/site-packet.json \
     --report /protected/owner-observation.json \
     --producer platform-owner --key /protected/owner-signing.key \
     --output /protected/receipts/site-revision-1.json
   ```

   Publication verifies packet/value bindings and original bytes. It creates a
   new mode-0600 receipt exclusively; existing observations are never overwritten.
   The signature is over `multi-tenant/commissioning-receipt/v1`, one NUL byte,
   then the canonical report. Inventory never receives the private signing key.
4. Mount the receipt and original bytes at their signed absolute paths. Set
   `INVENTORY_COMMISSIONING_EVIDENCE_FILE` to the protected registry. Each producer
   has an ID, base64 raw 32-byte public key, expiry, allowed field IDs and receipt
   paths. Enroll trust independently of the operator/browser who supplied inputs.
   Use an atomic registry replacement when adding, revoking or rotating producers.
5. Recheck evidence in the Console. Registry, signatures, field allowlists,
   tenant/site/packet/configuration/value bindings, time and original byte digests
   are revalidated on each read. Change an input and publish a newly bound receipt.
   Remove old receipts for the same field; conflicting current observations hold.

All paths must be absolute, nonsymlink regular files with no group/world write
access. The signing key also denies group/world read access. Bounds are 32
producers, 128 aggregate receipts, 32 checks per report, 8 MiB per original file
and 32 MiB of matching evidence per read. Inventory opens no browser-supplied path
or URL. Missing configuration gives unverified fields; malformed evidence never
becomes verified. Producer expiry bounds the displayed observation expiry.

A verified field means an enrolled owner signed that scoped result and its bytes
are intact/current. It is not independent native qualification, proof of all
permissions or an operating acceptance. Q05–Q10 still consume their original
campaign records and exact candidate/tuple/receiving decisions.

## AHV discovery bounds

Prism v4 lists now use explicit zero-based `$page` and `$limit=100`. The collector
allows `min(enrollment.max_pages, 10)` pages per resource list, at most 1,000
observed rows per list and 52 total native reads. Collection submissions and Console responses remain
bounded to 2 MiB; a very large combined workspace must be scoped accordingly. Every request rechecks the live
lease/authority, charges the shared endpoint budget and rereads credentials.
Response links are never followed. Changed totals, duplicate IDs, short pages,
missing counts, out-of-budget or expired collection hold the whole profile.

Inventory admits the corresponding variable read receipt, including the minimum
number of pages implied by returned resources. Scope filtering and native hashes
remain intact. The existing lease/deadline is unchanged: lower request budgets or
slow environments may hold a large discovery. Numbered pages are an observation
window, not a transactional native snapshot or an unlimited-scale claim.

## Interrupted export reads

A schema-version-2 `vmware_export_archive` artifact may explicitly set
`range_continuation: true`; the artifact digest binds this choice. The default
continues to hold an interrupted download. The opt-in path allows at most two
continuations in the **same live export lease**, only after receiving bytes with
a known total, `Accept-Ranges: bytes` and a strong ETag.

Each continuation rechecks current authority/lease/deadline and sends an exact
`Range` plus `If-Match`. Only matching `206`, ETag, Content-Range and remaining
Content-Length are accepted. Prefix length/hash and validator hash are journaled;
lease URLs/credentials are not. Local disk or journal failure holds. The completed
stream still passes the native manifest/full hash and OVF validation before lease
completion. HTTPS tests exercise real sockets with synthetic native data.

A process restart, expired lease, weak/missing validator, changed object, ignored
range, exhausted retries or unknown native write still requires reconciliation.
No native create/import is replayed and no automatic source failback is added.
Actual NFC range support must be measured on the selected installed tuple.

## Remaining high-level gaps

| Gap | Software advanced here | Actual next prerequisite |
| --- | --- | --- |
| Native end-to-end migration | Task-specific commissioning and attributable evidence handoff | Enrolled VMware/OpenStack lab and exact workload; Q05–Q07, then the initial AHV tuple |
| Commissioning console | Context, applicable fields, owner actions, signed evidence and expiry | Independently enroll the real producers and publish their observations |
| Guest, security and enterprise services | Protected, field-scoped owner evidence publication | Select concrete owner endpoints/protocols and guest recipes, then implement/qualify those adapters |
| Recovery | Opt-in same-lease interrupted export continuation | Native range qualification; cross-process reconciliation, application delta and post-write recovery campaigns |
| Platform/workload coverage | Larger bounded AHV discovery | Separate Windows, UEFI, appliance, warm/live and other-direction implementations/campaigns |
| Hosting and brownfield lifecycle | Distinct provision/adopt/operate/retire input requirements | Actual guest, service, identity, backup and lifecycle owner integrations |
| Production operation and scale | Bounded pagination, per-read budgets and evidence resource limits | Real workload/concurrency targets, monitored restore/upgrade/load and receiving rehearsals |

`release/p07-native-inputs.json` still has unknown owner/observer/evidence inputs;
`release/operating-inputs.json` remains held; `release/p10-inputs.json` has no selected
tuples, artifact set or receiving reviews. This change does not invent those
records or close BL-P07-001, BL-P08-001/002 or BL-P10-001/002.

## Verification entrypoints

- Inventory: Ruff, mypy, all tests with `P04_POSTGRES_BIN`; readiness tests cover
  tamper, scope/revision changes, expiry, revocation, file permissions and signing.
- Inventory worker: pagination tests include boundary counts, repeated/missing
  pages, changed totals, budget and revocation failures.
- Lifecycle worker: real HTTPS continuation, full archive/manifest tests and
  authority/disk/journal/validator failure cases; no native platform is simulated
  as qualified.
- Console: PHP feature/type/format checks, TypeScript/build, and P08 browser
  journeys for context, recovery, expiry, mobile layout and revoked access.
- `scripts/p08/check_readiness.py`: new schema fixtures, preserved legacy wire
  shapes, rejected authority injection and task/method combinations.
- `scripts/p08/qualify.py` and `qualify_browser.py`: exact-source CI reports.
