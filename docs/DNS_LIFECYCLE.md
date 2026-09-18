# Scoped DNS lifecycle — native service-owner integration

## Architectural role

The service owner writes authoritative DNS only after receiving an accepted allocation
and name assignment from the existing authority. The integration does not allocate
addresses, discover servers, infer ownership from names, or reach tenant management.
It belongs to shared-service commissioning and workload service attachment (P3/P5),
with retention and safe reuse handled during P6. Terraform remains responsible for
its independently owned native infrastructure resources.

The upstream [authoritative IPAM handoff](engineering/authoritative-ipam-allocation-handoff.md) records only an opaque allocation reference in this repository. The DNS owner resolves the exact assigned value through the approved IPAM/name-assignment authority before issuing a DNS scope; a repository example, allocation handle or failed IPAM call can never supply a guessed A/AAAA/PTR value.

The selected candidate interface is standards-based RFC 2136 UPDATE with HMAC-SHA256
TSIG over TCP. Actual server support, key/name/type policy, management transport,
clock synchronization, topology and secondary/cache behavior require site acceptance.
This is a proposed implementation profile, not a claim that the user's DNS server
supports it. RFC 2136 covers one zone per atomic update and excludes TTL from its
prerequisite equality; TSIG supplies message authentication, not confidentiality.
See [reviewed sources](../sources/increment03_references.json).

## Accepted inputs and ownership

A job contains version, explicit enabled flag, canonical operation UUID, tenant and
resource IDs, authoritative zone/server/port, key identity, engineering reference,
validity, prior ownership generation, and one to eight exact A/AAAA/PTR record sets.
A separate scope contains the same identity plus an accepted transport reference and
exact allowed names, values and TTL ceilings. **Version 2** additionally binds every
A/AAAA/PTR RRset to an opaque authoritative-IPAM allocation reference and positive
allocation generation. The job carries only the SHA-256 of those independently supplied
bindings. The scope should be issued/read-only through the existing change/engineering
process after the DNS owner resolves the exact values from authoritative IPAM; it must
not be edited to rubber-stamp a job. No supplied status, allocation handle or reference
string independently proves approval or IPAM authenticity.

Names are lower-case ASCII absolute names. Wildcards, aliases, delegation changes,
SOA edits, apex records, bulk deletes and unrecognized properties are excluded.
PTR names must be exact address reverse names; classless reverse alias creation is
not implemented. There is no unowned adoption path. Existing unmanaged name data
requires a separately reviewed ownership-transfer design, not deletion by this tool.

Each record group receives an opaque `hosting-v2` generation marker, and each record
owner name receives `_hosting-owner.<name>` with the same generation. The marker binds
the owner, DNS operation ID, exact resulting RRset payload digest **and** the accepted
IPAM-binding digest. The latter prevents a second owner from claiming AAAA for an
existing A name or reusing the name immediately after its address data is retired.
The native key ACL must cover only the accepted A/AAAA/PTR names and those exact TXT
marker names, not an unrestricted zone subtree. Markers are concurrency/ownership
records; they are not secret authentication tokens and do not replace IPAM evidence.

## Before any native write

1. Accept the actual authoritative primary endpoint and its exact zone. No NS/SOA
   auto-discovery or response-link following is used.
2. Accept the name/address assignment, resource and tenant ownership, operation
   lifetime, TTL and reverse-zone relationship. For every RRset, retain the opaque
   authoritative-IPAM allocation reference and generation that supplied the exact value.
   Do not derive allocations from examples, documentation ranges or allocation handles.
3. Establish scoped key custody and exact server-side update privileges, including
   the generated marker names. Verify negative access in an authorized target fixture.
4. Establish a protected management transport. TCP+TSIG is not payload encryption;
   an accepted network or tunnel mechanism must meet the applicable confidentiality
   requirement. This tool does not create or attest that mechanism.
5. Inject the secret from the authorized environment. Review the job/scope without
   exposing credentials. Keep initial workload quarantine and operating gates intact.
6. Run explicit read-only observation using a new private journal. Review the result
   and exact proposed record deltas. Re-observation does not renew authority.
7. Execute the explicit approved-change command with another new journal. The tool
   revalidates expiry immediately before attempting the update.

## Native sequence and crash behavior

The client authenticates each exact-zone/record query, requires authoritative replies,
rejects aliases and requires the named zone's SOA in negative observations. It compares
expected current values and ownership before deciding whether to send an UPDATE.

The UPDATE repeats value/existence prerequisites **at the authority**. On first claim,
both target names and owner markers must be absent. For an owned change, the old
`hosting-v2` marker, previous IPAM-binding digest and exact before RRset members must
match. CNAME absence is explicit. All changes and all markers are committed in that
single-zone transaction or none are.
A race between two first claimants produces one winning transaction, not split A/AAAA
ownership. TTL is inspected before/after but cannot be a server-side equality
precondition under RFC 2136; exclusive ownership remains a required operating control.

The private journal is reserved with exclusive creation before contact. A pending
attempt is recorded before mutation. At most one UPDATE is sent by an invocation.
Timeout, EOF, invalid authenticated reply or lost connection after send is **unknown
outcome**, not proof that the server did nothing. The client makes read-only queries
and compares the exact new generation and record values. There is no blind retry.
Power-loss durability of the chosen filesystem/journal transport remains an operating
qualification; a local JSON file is not an enterprise immutable evidence store.

## Results and operator action

| Result | Meaning and next action |
|---|---|
| INPUT_CHECKED_NO_TARGET_CONTACT | Shape/scope checked locally only; no native observation or authorization. |
| READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE | Expected before state observed; still no change or approval issued. |
| CONFLICT_NO_UPDATE / PREREQUISITE_CONFLICT | Stop. Reconcile ownership/current values and source before a new approved operation. |
| APPLIED_OBSERVED | Authenticated success plus exact authoritative after state; downstream propagation is not proven. |
| ALREADY_APPLIED_OBSERVED | Requested generation and values already observed; no second UPDATE. |
| RECONCILED_APPLIED_OBSERVED | Reply was uncertain but exact after state was observed; retain uncertainty/reconciliation events. |
| UPDATE_REJECTED | Authority rejected the update; do not broaden key privilege or bypass controls automatically. |
| INCONCLUSIVE_NO_UPDATE | Required initial observation unavailable; no UPDATE was attempted. |
| APPLIED_READBACK_INCONCLUSIVE / APPLIED_BUT_READBACK_DIFFERS | Keep activation held; discover actual state and competing changes. Do not delete successful data automatically. |
| UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION | Preserve the journal, operation identity and owner; investigate current authoritative records before any new mutation. |

## Forward/reverse, migration and retirement

A single invocation covers one authoritative zone. A forward A/AAAA group and reverse
PTR normally require different zone transactions and possibly different keys/owners.
The implementation procedure coordinates them as accepted steps, not a fabricated
atomic multi-zone operation. Reverse failure preserves the successful forward change
and holds activation; an approved resume uses exact observation and the same intended
identity. Cross-zone automatic compensation is not implemented.

During migration, publish only accepted source/target values and selected TTLs. Verify
negative caching, resolver and secondary convergence independently; authoritative
readback is not proof that all consumers see the new target. Writer fencing and
application/data cutover remain outside DNS mutation.

Retirement deletes only the exact owned address/PTR RRsets and updates tombstones.
Retain the `hosting-v2` marker while IPAM release cleanup/quarantine, address/name reuse,
stale records, log attribution, certificates and retained-copy obligations are assessed.
DNS deletion does **not** release or make the IPAM allocation reusable. There is no
automatic tombstone-release command. A future release/adoption design needs authority,
retention checks and tests.

## Qualification boundary

The local campaign exchanges real TCP DNS/TSIG bytes with an intentionally bounded
in-memory authority and runs the actual client. It tests transactions, races, denied
privileges, aliases, stale TTL, tombstones, IPAM-binding changes, invalid trust and lost
responses. It does not certify BIND, Windows DNS, an appliance, DNSSEC, recursion,
delegation, secondary replication, distributed durability, GSS-TSIG, the actual server
ACL or the external IPAM service. Version 1 ownership markers are not automatically
adopted by this candidate v2 profile; no native v1 qualification existed to preserve.
