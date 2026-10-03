# Application comparison through the operator command

Reviewed 30 September 2026. This B19/B20 increment follows the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It connects the installed operator to the [reviewed application assessment
service](application-comparison.md). It does not start provisioning, acquire a
reservation, approve an owner or advance a migration workflow.

## Explicit selections, without hand-authoring a request body

Install the existing control-plane extra and use the enterprise SSO process.
Supply one short-lived access-token line on stdin. The HTTPS origin, IDs and
`DRAFT_RECORD_DIGEST` below are placeholders, not real site inputs; replace the
digest with the lowercase SHA-256 `recordDigest` of the exact saved draft.

```sh
hosting-operator --api-url https://control.example --token-stdin assessments compare-application \
  --source-environment source --source-generation 7 \
  --application-group app-1 --draft-revision 1 --draft-record-digest DRAFT_RECORD_DIGEST \
  --member-profile db linux-uefi --member-profile web linux-uefi \
  --destination target-a 7 --capacity target-a pool pool-1 \
  --destination target-b 7 --capacity target-b pool pool-1 \
  --method COLD_VM_CONVERSION --network-mode routed --data-mode offline
```

Global `--ca-bundle` remains available for the selected enterprise CA. The
command sends one POST to `/v1/assessments/applications/compare` with no automatic
retry, redirect, token renewal, inventory recapture or job submission. It does not
fetch a newer draft or inventory generation to repair a refused selection.

Every retained logical workload needs one explicit `--member-profile`. The server
reconstructs actual membership and native IDs from the signed-review-bound draft;
CLI arguments cannot replace those members. The application contains 2–100 members
and 2–20 distinct destination environments, with at most 200 member/destination
combinations. Limits reject excess requests rather than truncate them. All selected
source/destination generations and the draft revision must be positive signed-64-bit
integers; booleans, zero, overflow, duplicate identities and ambiguous selectors
are refused before HTTP.

Optional `--capacity` identifies one exact observed pool, cluster, quota or
datastore for a selected destination. Omitting it retains an unknown capacity
assessment; the client does not infer a pool or combine capacity across pools.
Method, network mode and data mode are common to this calculation, with individual
guest profiles. This command does not implement heterogeneous per-member methods.

## Response interpretation version 2

The application report is now `hosting-application-comparison/2`. Both calculated
and held reports include `selectionDigest`: SHA-256 of compact, sorted-key,
ASCII JSON for the **decoded canonical selection**, with non-finite numbers
forbidden. It binds source environment/generation, application group, draft
revision/record digest, ordered member-profile pairs, ordered destinations and
optional capacity selectors, method, network mode and data mode. A missing capacity
selection is represented by omitted capacity fields, not explicit null fields.
This is not a hash of HTTP formatting, a signature, owner approval or native evidence.

The previous report did not bind method/network/data selections in its returned
fields. The new client rejects format 1 rather than silently interpreting that
response. No compatibility alias is introduced. Single-VM comparison remains
`hosting-discovery-comparison/1`; its command syntax and endpoint are unchanged.
Deployment must update the application-comparison service before relying on the
new command. Old clients consuming the application report need explicit migration.
No database, inventory, signed owner-review or normalizer format changes are needed.

The operator validates the embedded review using the existing review client
contract, then checks the application envelope against the exact in-memory request.
It verifies source and destination references, selected capacity identities, the
complete member/profile set, consistent native identities across destinations,
startup membership and false ownership/execution/reservation flags. A wrong method's
selection digest, a missing member or a substituted pool cannot be printed as a
valid response. The response is strictly decoded under a 1 MiB limit with duplicate
keys, invalid encoding, excessive nesting and numeric overflow rejected.

The client also checks internal report consistency: missing or insufficient
capacity needs the matching unknown/blocker issue, no selected/observed pool
cannot advertise available capacity, baseline required quantities must agree
across destinations, and member and aggregate statuses must retain the most severe
finding. It does **not** rerun placement, sum native disk layouts, verify owner
signatures, establish native freshness or qualify route support. Those authorities
remain at the authenticated API and their independent evidence owners.

## Outcomes and remaining holds

| Result | Meaning |
|---|---|
| Exit 0 | A validated calculation or `HELD_APPLICATION_REVIEW` report was received; not eligibility, reservation, approval or execution success. |
| Exit 2 | The API refused the request. Only the bounded error code/status is emitted; no native error detail or alternative request follows. |
| Exit 3 / `INVALID_INPUT` | The local selection is malformed; no API request was made. |
| Exit 3 / `APPLICATION_COMPARISON_RESPONSE_INVALID` | The successful-looking response is malformed, mismatched, oversized or not exactly HTTP 200. No partial report is printed. |
| Exit 3 / `API_UNAVAILABLE` | The HTTP operation failed; there is no retry, stored-result fallback or native action. |
| Exit 130 | Interrupted; no partial result is printed and no automatic continuation occurs. |

Unreviewed, revoked, stale, incomplete and superseded reviews stay held. Unknown
external dependencies are not made authoritative by source labels. Even all-member
eligibility remains conditional on application-wide policy/data review and actual
reservations. Logical baseline demand excludes staging/rehearsal copies, retained
source, physical-storage effects and recovery/HA headroom, as in the service contract.

`provisioner/cli/assessments.py` owns comparison parser/request/reply contracts,
including the existing single-VM request builder migrated out of `operator.py`.
The existing operator remains the sole HTTP transport for these commands. It
composes its standard-library-only draft and assessment helpers, which do not
import one another, the control plane, local execution service, SQL or native
adapters. Architecture tests constrain this exact dependency boundary, including
relative imports. Installed-package checks load the actual helper outside the
checkout; no wrapper or new executable was added.

Tests cover canonical selection digests, all-member and all-destination coverage,
invalid review/source/pool bindings, malformed/overflowing numbers, capacity/status
contradictions, held reports, strict HTTP/JSON limits, interruption and one-request
failure handling. API integration runs the command against the actual application
service and independent signed-review fixtures; these are not installed vendor
qualification. Report final-revision CI and local skips separately.

## Wave transition

This completes the CLI access slice of B20, not all of Wave 2. The
[saved-application browser](application-comparison-browser.md) now uses the same
format-2 API with unchanged-draft selection and stale-result clearing. Guided draft
creation/membership/evidence editing, independently verified external dependencies,
remaining image/hardware/security facts, inventory-visibility reconciliation and
B22 scheduling/freshness/resumable publication/estate qualification remain open.
Wave 3 B23/B24 still require commissioned envelopes, capacity/IPAM/staging
reservations and immediate per-effect authority. No comparison outcome is promoted
into a provisioning job or used to claim that those dependencies are complete.
