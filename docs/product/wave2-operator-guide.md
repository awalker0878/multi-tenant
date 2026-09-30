# Wave 2 operator guide: observed inventory and destination comparison

Status: authenticated ingestion and read-only destination comparison are
implemented in the repository, alongside the installed collector and revisioned
application-draft API. Production deployment and site qualification remain open. See the
[architecture and acceptance sequence](wave2-discovery-architecture.md).

## Read an authorized generation

Sign in through the enterprise SSO control API described in the
[control-plane operator guide](control-plane-operator.md). First check
`GET /v1/access/scopes`, then select an environment with
`GET /v1/environments?wsdId=<WSD>`. These environment rows are
`DECLARED_UNVERIFIED` human selectors. They do not show that a platform has
been contacted or that its inventory exists.

For a selected environment, the following read-only endpoints are implemented:

| HTTP request | Result | Access and limits |
| --- | --- | --- |
| `GET /v1/environments/{id}/discovery/generations?limit=50&after=0` | A page of generation IDs, capture times, result digests, `COMPLETE`/`PARTIAL`/`UNKNOWN` coverage, object counts and error/privilege counts. | Exact native-scope `JOB_READER` or `EXECUTION_OPERATOR` grant; `limit` 1–100; `nextAfter` for the next page. |
| `GET /v1/environments/{id}/discovery/generations/latest` | The latest generation summary, or not found if none exists. | The same exact native-scope grant; indexed lookup without scanning history pages. |
| `GET /v1/environments/{id}/discovery/generations/{generation}/objects?limit=50` | A page of stable native IDs, resource kinds, optional display names, unknown-fact counts and object digests. | The same exact environment scope and generation; `limit` 1–100; opaque `nextAfter` cursor. Raw collector facts and credentials are not returned. |

A missing environment or grant appears as not found. A read may return
`DISCOVERY_UNAVAILABLE` when the discovery repository is not configured. An
empty list means no published generation is available through that scope; it
does not prove the native environment is empty. Record the generation and
result digest when discussing a candidate. `PARTIAL` or `UNKNOWN` coverage
cannot establish absence or retire a previously seen native object. A VM name
is a display value; the endpoint, native scope, platform family, kind and
native ID form its identity across renames.

The thin CLI has read-only commands for these pages. Each invocation obtains
one short-lived SSO token on standard input, as described in the control-plane
guide:

```text
<approved SSO token source> | hosting-operator --api-url https://control.example.org --token-stdin discovery generations --environment env-01
<approved SSO token source> | hosting-operator --api-url https://control.example.org --token-stdin discovery objects --environment env-01 --generation 1
```

Pass the response `nextAfter` to `--after` to continue either listing. The
portal shows the latest generation and paged identity summaries for an
authorized environment, including coverage and collection gaps. It clears
stale rows if the selection changes or a page fails. No operator write
endpoint admits a discovery campaign or accepts native rows.

## Compare authorized destinations

The portal's **Compare migration options** section uses the selected source's
observed VM inventory. Select the workload, then a destination WSD and **Show
destinations**. Add the latest observation for each candidate. The source and
destination generation numbers remain pinned during comparison; changing scope
or logging out clears stale selections and results. Supply the method, guest
profile, network mode and data mode. Where capacity should be evaluated, select
the observed capacity kind and exact native ID for that destination.

The equivalent CLI command is:

```text
<approved SSO token source> | hosting-operator --api-url https://control.example.org --token-stdin assessments compare --source-environment source-01 --source-generation 7 --workload-native-id vm-01 --destination target-01 3 --destination target-02 4 --capacity target-01 pool pool-01 --method REBUILD_RESTORE --guest-profile linux --network-mode routed --data-mode backup-restore
```

Repeat `--destination ENVIRONMENT GENERATION` for 2–20 distinct destinations.
The source cannot also be a destination; two declarations for the same native
endpoint/scope cannot count as distinct candidates. `--capacity ENVIRONMENT KIND NATIVE_ID`
is optional per destination; supported kinds are `pool`, `cluster`, `quota` and
`datastore`. These values select observations; they do not assert qualification.

The authenticated API is `POST /v1/assessments/compare`. Its request has no
operator-supplied tuple claims, reviews, credentials or success flags:

```json
{
  "source": {"environmentId": "source-01", "generation": 7},
  "workloadNativeId": "vm-01",
  "destinations": [
    {"environmentId": "target-01", "generation": 3,
     "capacityKind": "pool", "capacityNativeId": "pool-01"},
    {"environmentId": "target-02", "generation": 4}
  ],
  "method": "REBUILD_RESTORE",
  "guestProfile": "linux",
  "networkMode": "routed",
  "dataMode": "backup-restore"
}
```

Each selected environment needs the same exact-scope read grant as inventory.
Missing installation proof or scope access refuses the request without exposing
foreign identities; unavailable assessment configuration returns
`ASSESSMENT_UNAVAILABLE`. Configure the independently signed durable inputs in
the [assessment evidence guide](../operations/assessment-evidence-ingest.md).
Missing route or control evidence produces explicit unknowns. The response pins
raw and normalized input digests and reports `executionAuthorized: false`.
It also identifies a selected generation superseded by a newer observation.
Historical pins remain unchanged; any newer source or destination generation,
including partial or unknown coverage, withholds current eligibility with a
snapshot-superseded reason. Refresh the selection and review the new inputs
rather than carrying an earlier positive result forward.

## Interpret a destination assessment

The service compares installed destinations against one observed native VM in
a deterministic order. Each directed route binds exact source and destination organization,
tenant, site, WSD, endpoint, native scope, product tuple ID and digest, method,
guest profile, network mode and data mode. Reverse direction and same-family
site moves need their own route records. Source and target qualification
artifacts are independent and expire separately.

| Status | Operator interpretation |
| --- | --- |
| `ELIGIBLE` | Current, complete and verified inputs satisfy the read-only comparison rules. This is an informational candidate, never execution permission. |
| `CONDITIONAL` | A known route qualification condition still needs remediation and review. |
| `BLOCKED` | A hard mismatch or reviewed failure exists, such as unsupported method/profile, insufficient selected capacity, failed control or cross-tenant destination. |
| `UNKNOWN` | A necessary fact or independently verified authority/evidence is absent, stale, incomplete, conflicting or not bound to the exact snapshots. |

Every issue has a code, plain reason and suggested remediation. The engine
requires a current exact source and destination read selection for the same
operator; an ungranted target cannot appear eligible. It also requires source
CPU, memory, disk, guest, network and data facts; selected target capacity
and compatibility facts; and independent policy translation, security
equivalence and recovery reviews tied to both generation digests. Estimated
copy time, when measured size and throughput exist, has **low** confidence and
describes only the arithmetic copy phase. It is not an outage estimate.

Application drafts are now stored as UNREVIEWED proposals with an authenticated
author and explicit known/unknown dependencies. The asserted owner is not the
verified author and saving does not accept membership. The separate reviewed-
candidate model still requires exact external owner review. Brownfield adoption
remains a no-change review artifact; none of these drafts adopts or mutates a VM.

## Save and read an application draft

Use `PUT /v1/environments/{id}/application-drafts/{applicationGroupId}` with an
exact-scope EXECUTION_OPERATOR grant, current inventory generation/result digest,
`expectedRevision` (zero for a new draft), `draft` and `dependencies`. See the
[complete request contract](../engineering/application-drafts.md) for the bounded
member, dataset, consistency, startup and dependency fields. Duplicate/extra fields
and caller-supplied approval or actor claims are rejected. The
[operator CLI and bounded listing](../engineering/application-draft-operator.md)
now provide save/load/history with explicit revision/source pins. A draft-editing
portal is not supplied yet.

Read latest draft state with GET on the same route, or select immutable history
with `?revision=N`. JOB_READER and EXECUTION_OPERATOR may read within their exact
native scopes. Editing appends a revision; it never overwrites history. A 409 means
the expected revision or new-save source selection changed: review the new state
rather than automatically retrying modified content. An exact lost-response retry
can return the original, now-superseded source pin with `sourceSuperseded: true`.
That flag does not assess source freshness or completeness. Every response remains
UNREVIEWED, without accepted ownership or execution authorization.

## Site qualification still required

The current VMware REST reader covers only VMs visible in independently
selected folders, with a 4,000-visible-VM list limit and no native cursor.
Inherited privilege gaps can hide objects. The AHV adapter assumes a pinned
Prism Central VMM v4.0 installed profile and exact cluster; the OpenStack
adapter assumes pinned HTTPS Nova/Cinder/Neutron catalog roots and a
project-scoped read role. All three now have actual bounded HTTPS clients and an
[installed stage/publish command](../engineering/discovery-collector-runtime.md).
Protocol/integration tests are not proof of deployed custody or complete coverage.

Before publishing production observations, the site owner must select and
qualify the actual installed API/product tuple, constrained read credential,
endpoint routing, paging/permission coverage and an independent inventory
reconciliation. Deploy the separate [discovery ingest service](../discovery-ingest.md)
with its dedicated PostgreSQL role, pinned mTLS/PKI, independently signed issuer
and collector enrollment, fresh native read-credential witness and durable
signature custody. Its implemented verifier refuses missing or invalid inputs.
The independent campaign/witness producers and native collector credential
retrieval still require actual site integration and qualification. Owner/security teams must qualify
policy translation, recovery, capacity and the selected route on actual
source and destination sites. The proposed 50,000-workload/100-endpoint
benchmark and p95 under two seconds remain unmeasured acceptance targets.

Discovery is a way to investigate movement. Provisioning, transfer, source
fencing, cutover and useful-service verification remain later implementation
and release gates.
