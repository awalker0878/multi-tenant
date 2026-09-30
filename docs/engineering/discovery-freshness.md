# B22 — scoped inventory freshness inspection

Reviewed 30 September 2026. This increment stays in
[Wave 2 of the existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It adds an on-demand read projection, not a recurring monitor, alert dispatcher,
native collector, scheduler or migration-approval path.

## Read the latest stored capture

```text
GET /v1/environments/{environment_id}/discovery/freshness
Authorization: Bearer <current enterprise token>
```

The environment and token are deployment inputs, not supplied examples of authority.
The existing HUMAN identity boundary and exact native-scope JOB_READER or
EXECUTION_OPERATOR grant apply. No query parameters are accepted: callers cannot
select an older generation, weaken the threshold or request force/refresh behavior.
The endpoint is composed by the existing API server when discovery is configured;
there is no new server, CLI executable, browser view or service account role.

`discovery/freshness.py` owns the calculation and
`api/discovery_freshness.py` its transport. The repository reads the latest stored
generation twice. Identity, role and environment selection are rechecked around
both reads, including when no inventory exists. Changed generations or metadata
produce a conflict rather than a hidden retry, substitution or older-data fallback.
This is LIVE_METADATA_RECHECKS, not one atomic estate/trust snapshot or a promise
that nothing can change after the final check.

## Age is not completeness

The API currently uses a server-owned refresh interval of 3,600 seconds and maximum
age of 86,400 seconds. These are explicit engineering monitoring defaults, not
vendor limits, an SLA, a scheduled collection cadence or mutation authority. The
maximum-age boundary matches the existing inclusive default assessment interval,
but this report neither changes nor overrides that engine's separate policy.
The service accepts a bounded immutable policy at construction; the HTTP endpoint
does not expose caller overrides or a deployment configuration switch in this slice.

| Field/state | Meaning |
|---|---|
| MISSING | No persisted generation exists under the selected authorized scope. Observation and age are null. |
| FUTURE_CAPTURE | Capture time exceeds the checked UTC time, even by one microsecond. Age is null, not clamped to zero. |
| FRESH | Nonnegative capture age is at most the configured maximum. This says nothing about completeness or eligibility. |
| STALE | Capture age is strictly greater than the configured maximum. |
| refreshDue | True at or beyond the refresh interval, or for missing/future capture. It is an age signal, not a queued request. |

At exactly one hour a refresh is due; at exactly 24 hours the default age test is
still FRESH; one microsecond later it is STALE. Age uses the original capture time
and exact integer microseconds, including after slow reads. It never uses inspection,
publication or restart time to make old inventory look new. Clients must preserve
integer precision and treat null separately from zero. UTC-invalid or regressing
inspection clocks refuse the report instead of returning apparently fresh data.

Reported COMPLETE, PARTIAL and UNKNOWN collection quality remains separate. A
recent partial capture can be FRESH while still carrying COLLECTION_PARTIAL,
COLLECTION_ERRORS_PRESENT and MISSING_PRIVILEGES issues. A complete zero-object
capture is not MISSING. The newest partial/unknown generation is never replaced
with an older complete one. The response always includes NATIVE_VISIBILITY_UNVERIFIED.

## Response and error contract

`hosting-discovery-freshness/1` contains exactly `format`, `environmentId`, `scope`,
`checkedAt`, `policy`, `observation`, `freshness`, `ageMicroseconds`, `refreshDue`,
`issues`, `consistency`, `integrityVerification`, `nativeVisibilityVerified`,
`collectionRequested` and `executionAuthorized`.

`scope` retains the seven organization/tenant/site/security-domain/endpoint/native-
scope/platform fields using the repository's snake_case names. `policy` contains
`format: hosting-discovery-freshness-policy/1`, `refreshAfterSeconds` and
`maxAgeSeconds`. A non-null observation contains `generation`, `campaignId`,
`authorizationDigest`, `resultDigest`, `capturedAt`, `completeness`, `objectCount`,
`collectionErrorCount` and `missingPrivilegeCount`. No raw observation, credential,
provider error body or privilege name is returned. Missing/due/stale/future,
collection-quality, error and missing-privilege issue codes retain their separate
causes. Inspection does not rewrite captures, generations, approvals or audit rows.

Every report is no-store and explicitly carries `integrityVerification: METADATA_ONLY`,
`nativeVisibilityVerified: false`, `collectionRequested: false` and
`executionAuthorized: false`. Stored metadata shapes, counts, digests and scope are
validated, but the endpoint does not rehydrate the original signed payload or
reverify its current signer/native-credential authority. That evidence remains
with the existing ingest, signed assessment and native qualification owners.
A digest-shaped field or FRESH status is not proof of current signature validity.

Anonymous/invalid credentials receive 401; non-human principals receive 403.
Unknown or inaccessible environments receive the same 404. Revocation or identity
change after a metadata read withholds the result. Concurrent inventory changes
return 409 DISCOVERY_FRESHNESS_CHANGED. Any query argument returns 422.
Disabled discovery returns 503 DISCOVERY_UNAVAILABLE. Invalid metadata, clock or
backend failures return 503 DISCOVERY_FRESHNESS_UNAVAILABLE rather than MISSING,
without raw exception details. Non-GET methods do not request a collection. A valid
200 response may be missing, stale or incomplete; HTTP success is not a health pass.

## Verification and remaining implementation

Service and API tests cover exact age boundaries, future/invalid clocks, missing
versus complete-empty inventories, recent partial/unknown captures, original-time
preservation, metadata substitution, tenant/scope mismatches and reader revocation.
The service performs no raw-object hydration or native I/O. Five disposable
PostgreSQL tests cover actual latest-generation reads, concurrent publication,
full-scope/tenant filtering, unchanged audit/inventory state and post-read denial.
Their ingest fixture uses the existing explicit test verifier; these are not new
native-signature or deployed-platform qualification campaigns. Local skips and
final-revision CI execution must be reported separately.

B22 still needs periodic monitoring, retained health history, alert delivery,
durable multi-process scheduling, globally coordinated endpoint budgets, larger
resumable publication and measured estate-scale acceptance. The
[batch staging path](discovery-batch-scheduling.md) remains process-local and is not
triggered by refreshDue. Other Wave 2 native-fact, visibility, dependency, authoring
and adoption obligations remain open. No Wave 3 work, SQL migration, additional
privilege, shim, native collection or production qualification is introduced here.
