# Wave 2 operator guide: observed inventory and destination comparison

Status: read-only repository implementation in progress. The production site
ingestion and native qualification path is not deployed. See the
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

## Interpret a destination assessment

The assessment engine currently runs inside trusted service code; it is not
exposed as a public API or CLI command. It compares at least two *distinct*
installed destinations against one observed native VM in a deterministic
order. Each directed route binds exact source and destination organization,
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

An application grouping is an owner-reviewed proposal with attributed and
unresolved dependencies, not accepted membership. A brownfield adoption
proposal is a no-change review artifact; ownership collision or unknown
facts hold it. Neither proposal writes a native object or adopts a VM.

## Site qualification still required

The current VMware REST reader covers only VMs visible in independently
selected folders, with a 4,000-visible-VM list limit and no native cursor.
Inherited privilege gaps can hide objects. The AHV adapter assumes a pinned
Prism Central VMM v4.0 installed profile and exact cluster; the OpenStack
adapter assumes pinned HTTPS Nova/Cinder/Neutron catalog roots and a
project-scoped read role. These are bounded, injected GET transports and local
conformance tests, not deployed native collectors or proof of coverage.

Before publishing production observations, the site owner must select and
qualify the actual installed API/product tuple, constrained read credential,
endpoint routing, paging/permission coverage and an independent inventory
reconciliation. A separately operated campaign issuer, signed authority,
enrolled worker, mTLS/PKI, read-only Vault role and result provenance verifier
must be wired to the dedicated PostgreSQL ingest role. The repository rejects
ingest without that verifier and role. Owner/security teams must qualify
policy translation, recovery, capacity and the selected route on actual
source and destination sites. The proposed 50,000-workload/100-endpoint
benchmark and p95 under two seconds remain unmeasured acceptance targets.

Discovery is a way to investigate movement. Provisioning, transfer, source
fencing, cutover and useful-service verification remain later implementation
and release gates.
