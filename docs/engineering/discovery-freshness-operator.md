# B22 — operator inspection of inventory freshness

Reviewed 30 September 2026. This continuation belongs to B22 in the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It exposes the existing [freshness inspection API](discovery-freshness.md) through
the installed operator. It is a one-shot read/check, not a scheduler, recurring
monitor, alert dispatcher, collector or migration qualification.

## Read and check commands

Install the existing controlplane extra, select the HTTPS API and obtain a current
scoped human token through enterprise SSO. The following origin and environment
are placeholders. Supply one token line on stdin, never in argv or a URL. The
existing global `--ca-bundle` option selects the approved enterprise CA when needed.

```sh
hosting-operator --api-url https://control.example --token-stdin discovery freshness --environment env-01
hosting-operator --api-url https://control.example --token-stdin discovery freshness --environment env-01 --check
```

Each invocation makes one GET to
`/v1/environments/{environmentId}/discovery/freshness`, without query parameters
or a request body. The existing HUMAN identity and exact-scope API read grants
remain required. No server refresh interval or maximum age can be overridden by
the command. There is no automatic retry, polling, stored-response fallback,
token renewal, collection request, inventory rebase or migration submission.

| Exit | Meaning |
|---|---|
| 0 without `--check` | A valid report was retrieved. It may describe missing, stale, due or incomplete inventory. |
| 0 with `--check` | The retrieved metadata is FRESH, not refresh-due, and reports COMPLETE collection without collection errors or missing privileges. Native visibility and signatures remain unverified. |
| 4 with `--check` | A valid report describes missing/future/stale capture, refresh-due age or incomplete/unknown collection. The original report is still printed on stdout. |
| 2 | The API refused the read; only bounded status/error identity is emitted. It is not evidence of MISSING inventory. Parser usage errors also use argparse's existing exit 2. |
| 3 | Local input, transport, or response validation failed. No partial report is printed. |
| 130 | Interrupted. No automatic continuation or partial report is printed. |

Response failures use `DISCOVERY_FRESHNESS_RESPONSE_INVALID`; local invalid input
uses `INVALID_INPUT` and HTTP transport failure uses `API_UNAVAILABLE`. Exception
strings, response bodies from failed reads and token values are not emitted in
errors. External monitoring can distinguish exit 4 from access/transport failures,
but must manage its own approved schedule, token lifecycle, retention and alerts.
This command does not implement that integration or install an automation.

## Exact capture metadata, not a health or execution authority

The client accepts only `hosting-discovery-freshness/1`, the exact requested
environment, the complete seven-field native scope and bounded policy/observation
shapes. It checks age arithmetic and issue consistency against the report's own
UTC `checkedAt`, original `capturedAt` and server-owned intervals. It does not use
local wall time to rewrite a result or declare a cached report current. Exact
integer microseconds are retained, including values beyond JavaScript's safe range.
The inclusive maximum-age boundary and refresh-due boundary stay distinct. Missing
and future captures have null age; a complete zero-object capture is not missing.

A recent partial observation can be FRESH yet return exit 4 in check mode. Even
check exit 0 retains `NATIVE_VISIBILITY_UNVERIFIED`, `METADATA_ONLY`, and false
native visibility, collection-requested and execution flags. Neither a COMPLETE
label nor a digest-shaped field proves complete native coverage, current signing
custody, capability support, capacity or migration eligibility. The API is trusted
for current identity/scope and metadata selection; the CLI does not independently
resolve that environment, verify signatures or rehydrate native observations.

HTTP 200 and one JSON content type are required. Freshness requests ask for identity
encoding and no-store behavior. Freshness replies are limited to 16 KiB; compressed
encoding, duplicate/ambiguous length/type headers and mismatched declared byte
lengths are rejected. The existing strict JSON reader rejects duplicate keys,
invalid UTF-8, excessive nesting, non-finite numbers and integer overflow. Numeric
strings/floats/booleans cannot masquerade as generation/count/age fields. Unexpected
fields, altered authority flags and missing/duplicated issue codes withhold output.
The existing bounded HTTP connect/read timeouts and TLS checks remain unchanged;
this increment adds no hard whole-invocation deadline or periodic watch.

## Implementation, tests and wave status

`provisioner/cli/discovery.py` now owns discovery parser/request and freshness reply
contracts. Existing generations/objects construction moved out of `operator.py`
without compatibility wrappers; their public command syntax and API queries remain
unchanged. The operator remains the HTTP owner and strict JSON decoder. The new
helper has only standard-library imports, with exact architecture checks against
controller, database, native-adapter and peer-command backreach.

`test_discovery_freshness_cli.py` covers exact boundaries, server policies, complete
empty versus missing captures, partial/error metadata, request isolation, malformed
replies, response limits, redaction, cancellation and old command contracts. Three
in-process tests use the actual authenticated API and freshness service to verify
two metadata reads and mid-read access revocation. Their repository port is an
in-memory fixture, not a real PostgreSQL or native-platform campaign. Final-revision
CI results and any local dependency gaps must remain separately recorded in PR #54.

The existing freshness service, API schema/policy, database and native collectors
are unchanged. The maintained RAD/TAD/interface/transition authority model remains
valid; no design approval, native qualification, migration or privilege change is
implied by this client increment. No new executable or database migration is added.

**Remain in Wave 2.** This delivers the operator freshness-inspection/check slice,
not full B22. Periodic monitoring/history/alerts, durable multi-process scheduling,
global endpoint budgets, larger resumable publication and estate measurements remain
open. Other Wave 2 native-fact, visibility, dependency, authoring and adoption gates
remain open. No Wave 3 implementation or wave-completion claim is introduced.
