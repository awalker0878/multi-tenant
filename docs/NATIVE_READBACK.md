# Native readback: configuration, realization and task completion

## Architectural position

This implementation closes part of Increment03 backlog I09. It observes resources
owned by the platform/network/security work packages after an interrupted or
completed change. It does not become their configuration owner. Existing change,
asset and evidence systems can store its input/output records; no custom hosting
application is required.

The [reference architecture](../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx)
requires independently attributable actual state and controlled recovery. The
[worked design](../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx)
retains the domain/edge/service identities. A readback manifest selects only the
native resources mapped by the accepted engineering record. Portable tenant labels
are not proof of platform tenancy or actual native RBAC.

## Scope and prerequisite record

Record the native management endpoint and certificate authority, installed product
and API version, principal/read privileges, portable tenant/domain/operation,
native resource paths/IDs, expected selected fields, revision/ETag and the known
native task or expected intent version. Keep the accepted expectation independent
of the observation. Do not obtain an untrusted current value, immediately call it
the expected value, and describe that as independent verification.

The two new profiles are deliberately explicit: `nsx-local-policy-v1-selected-fields`
and `nutanix-networking-prism-v4.3`. They do not automatically negotiate, downgrade or
copy the installed platform's advertised defaults. Missing expected fields are
unknown, including fields the native product may omit when empty. A profile whose
required fields/version tokens cannot be obtained needs an engineered, reviewed
normalization or a different observer; the code does not fabricate success.

## NSX Local Manager profile

Read each exact selected object through `/policy/api/v1`, then its corresponding
`GET /policy/api/v1/infra/realized-state/status?intent_path=...`, then the object
again. The selected configuration and `_revision` must not change around the
status read. Two identical completed samples are required. [N1–N4]

| Resource | Exact supported relative path | Mandatory selected configuration |
|---|---|---|
| Segment | `/infra/segments/{id}` | Identity/revision, connectivity and transport-zone paths, subnets, advanced configuration |
| Tier-1 | `/infra/tier-1s/{id}` | Identity/revision, upstream path and advertisement types |
| Static route | `/infra/tier-0s/{id}/static-routes/{id}` or Tier-1 equivalent | Identity/revision, network and next-hop list |
| Gateway policy | `/infra/domains/{id}/gateway-policies/{id}` | Identity/revision, category, sequence, stateful flag and selected rule list |
| Security policy | `/infra/domains/{id}/security-policies/{id}` | Same policy controls; this does not inspect the whole global hierarchy |
| Group | `/infra/domains/{id}/groups/{id}` | Identity/revision and expression list |

Expected policy rules include rule identity, unique sequence, action, direction,
address families, enabled/logged flags, source/destination membership **and their
negation flags**, scope, referenced and inline services, and profile list. Additional
expected nested fields can be included in rules. Lists retain order and exact
membership. The tool does not reorder expressions/rules into a seemingly equivalent
configuration. Negation and inline service changes are explicitly tested. [N3]

`intent_version` is recorded independently of the configuration `_revision`; this
implementation does not assume they are equal. Completion requires the expected
intent version, `publish_status=REALIZED`, consolidated `SUCCESS`, and `SUCCESS`
for exactly the accepted enforcing-system paths. Unknown, missing, duplicate or
unexpected span/status data prevents a match. Error and pending states remain
separate. An enforcement point in this response is a system/site, **not every ESXi
or Edge node**. This observer does not request or prove each node's enforced rules.
[N1]

No refresh POST, search, discovery, Global Manager or `/orgs/.../projects/...`
variant is implemented. Namespace/API path and authorization differences require
a separately supported profile. The documentation snapshot consulted identifies
NSX 9.1.1.0; it is not evidence that an installed NSX release or the retained
Terraform provider combination supports every field. [N1–N4]

## Nutanix networking and prism v4.3 profile

The SDK reference exposes exact VPC/subnet GET interfaces and an exact task GET.
The profile reads a **recorded single task**, reads the selected resources, then
reads the task again. Two stable completed samples are needed. Task IDs are opaque
and safely URL-encoded, including a documented SDK-style prefix/colon form; the
client does not invent a task UUID or follow a callback URL. [U1–U5]

| Read | Required identity and scope |
|---|---|
| VPC | `extId`, object type, native `tenantId`, name, type, external-subnet membership, externally routable prefixes and exact strong ETag |
| Subnet | `extId`, object type, native `tenantId`, name, type, VPC reference, external flag, IP configuration and exact strong ETag |
| Task | Exact task ID and operation, creation time within the operation, complete enumerated entity coverage, no subtasks/batch, terminal status and completion time |

The native `tenantId` is a platform identity, not the reference architecture's
`tenant-001` label. The engineering binding must establish the relationship.
Required ETag and task metadata must be independently recorded and actually
returned by the selected product. An absent ETag, weak ETag or omitted expected
field is unknown; a different strong ETag/configuration is a difference.

`QUEUED`, `RUNNING` and `CANCELING` remain pending. `FAILED` or `CANCELED` is a native
failure, **not proof that no resources were created**. `SUCCEEDED` is accepted only
with valid completion metadata, exact affected-resource coverage and no diagnostics
requiring review. Suspended, redacted and unrecognized status values remain unknown.
Composite tasks and limited/unresolved affected-entity lists are rejected rather
than treated as complete. This release neither lists nor cancels tasks. [U2]

VMs, Flow policies and route resources are not covered by the new Nutanix reader.
The profile's source dependency is networking/prism Go SDK v4.3.1; the code itself
uses standard-library HTTP rather than executing the SDK. No legacy API fallback
or installed compatibility claim is made. [U3–U6]

## Transport and evidence protections

The transport is GET-only through an exact generated path allowlist and a canonical
HTTPS origin. It verifies the server certificate/hostname and rejects redirects,
foreign response links, environment proxies and credentials embedded in an origin.
It does not create a session cookie or request credential renewal. The new clients
use task-scoped Basic credentials over TLS because that is the selected candidate
profile; stronger or different authentication requires an explicit integration.

Replies must be HTTP 200 JSON objects. Duplicate JSON keys, nonfinite numbers,
ambiguous framing, unsupported content encoding, weak/ambiguous ETags, oversized
bodies, truncated content, credential-shaped input and malformed nested data are
rejected. HTTP 404 is unknown, not deletion evidence. Error text and actual values
are not echoed into diagnostic reasons. Revision/hash comparisons do not grant
permission to rewrite the resource.

Default limits: 20 resources, 3 rounds (2–10 supported), 0.2-second inter-round pause,
5-second socket timeout, 60-second overall cooperative budget, 400 GET ceiling and
2 MiB body ceiling. These are implementation bounds, **not government-mandated
thresholds**. Remaining read time is applied to the live TLS socket, including
Connection:close responses. The operating system's hostname-resolution call is
not forcibly interrupted by that budget; use approved DNS and an execution-level
deadline for native runs. A slow-body regression proves the response-read budget,
not all resolver failure behavior.

The output path is created exclusively, without following a symlink, mode0600. An
initial incomplete record is written before contact; output is flushed and synced.
Interrupted/truncated journals cannot satisfy recovery. The directory must be owned
and protected independently. The JSON digest is an integrity consistency value,
**not an approval signature, immutable archive or source-authenticity proof**.

Two stable samples are observational evidence only. They cannot exclude changes
before/between/after the bounded sampling interval, prove all resources were
selected, or prove a compromised management API truthful. Preserve independent
quarantine, writer ownership and packet-path tests.

## Operator use

[Disabled NSX example](../examples/nsx_observation.json.example) ·
[Disabled Nutanix example](../examples/nutanix_observation.json.example)

Run without contact first. For accepted native observation, enable only the selected
manifest, supply the identical expected origin, inject credentials through the
approved environment and use a new private output. Native readback never writes
configuration or grants apply/delete/activation rights. CLI exit 0 means input-valid
or selected-field match, depending on mode; it is not an authorization result.

[N1–N4, U1–U6]: [Primary source register](../sources/increment04_references.json).
See [interrupted-change triage](INTERRUPTED_CHANGE_RECOVERY.md) before any subsequent
resource mutation.

The [native reconciliation assurance gate](engineering/native-readback-writer-fencing-and-reconciliation-assurance.md)
sits above this observer. A matching report is insufficient for recovery readiness until the exact installed API/RBAC/default/version-token behavior, accepted task/entity scope, current writer fence, containment state, operation generation and accountable reconciliation decision are separately evidenced. The active assurance index is intentionally empty.

## Optional bounded Nutanix task-tree profile

The original profile above retains its single-task constraint. A separate [known-tree profile](engineering/nutanix-task-tree-readback.md) now handles a fully enumerated small parent/child scope through the same transport, resource checks and recovery holds. Partial native child summaries and batch jobs remain unsupported; no automatic task listing, cancellation or version fallback is added. Follow the [explicit manifest and execution procedure](implementation/nutanix-task-tree-readback.md).
