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

VMs, Flow policies and route resources are not covered by this networking reader.
Separate [AHV VM](implementation/automation/nutanix-vm-readback.md) and
[Flow policy](implementation/automation/nutanix-flow-readback.md) snapshot profiles
are available, as are [vSphere VM/task observations](implementation/automation/vsphere-readback.md).
The optional [AHV VM/task profile](implementation/automation/nutanix-vm-task-readback.md)
combines VMM v4.2 snapshots with a bounded, explicitly recorded Prism v4.3 task
graph. It supports offline recovery review and campaigns v3/v4; it does not
discover other work or provide native fencing. The separate
[AHV activity profile](implementation/automation/nutanix-vm-activity-readback.md)
adds bounded queries for visible pending/late-completed tasks on those exact VMs.
Extra or uncertain activity holds. It supports saved-plan/ledger review of
existing AHV power/NIC lifecycle attempts while preserving the ledger hold.
Installed query semantics, retention and cross-writer visibility require native
qualification; these observations still provide no native fencing. Each
profile's exact coverage and task limitations are documented separately.
The vSphere clone activity profile additionally observes visible work on both
accepted template sources and result VMs, without clone submission, state adoption
or native writer fencing.
[VMware network association readers](implementation/automation/vmware-network-binding.md)
add exact NSX-backed distributed-portgroup/switch identities and segment-scoped
realized-switch identities. Campaign v6 binds these to each VM's assigned domain;
v7 adds exact distributed-port occupants, connection cookies and VM/NIC/host/MAC
bindings. Effective DFW membership and native qualification remain separate.
The [held vSphere reviewer](implementation/automation/terraform-recovery.md) now
requires those attachment witnesses alongside VM activity, binds retained disks
and NICs to the saved plan, and checks both reports under the same fence/quarantine
timing. Offline review rechecks selected network witnesses and both VM snapshot
digests; older witness-free reports require recollection. These consistency checks
preserve the ledger and do not authenticate a collector or create native fencing.
The profile's source dependency is networking/prism Go SDK v4.3.1; the code itself
uses standard-library HTTP rather than executing the SDK. No legacy API fallback
or installed compatibility claim is made. [U3–U6]

## Transport and evidence protections

The base profiles use GET-only access through an exact generated path allowlist
and a canonical HTTPS origin. The separate vSphere task-tree profile adds bounded
session-collector POSTs for filtered history creation, page reads and cleanup.
The port-attachment profile adds fixed, exact-key `FetchDVPorts` POSTs for reads;
neither supplies an infrastructure mutation interface. All profiles verify the server
certificate/hostname and reject redirects,
foreign response links, environment proxies and credentials embedded in an origin.
They do not create a login session or request credential renewal. The original
NSX/Nutanix profiles use task-scoped Basic credentials over TLS; vSphere uses an
independently issued VI session. Profile-specific authentication must be accepted
for the installed target.

GET replies must be HTTP 200 JSON objects. The vSphere history profile additionally
accepts bounded JSON arrays for pages and strict HTTP 204 collector cleanup.
Duplicate JSON keys, nonfinite numbers,
ambiguous framing, unsupported content encoding, weak/ambiguous ETags, oversized
bodies, truncated content, credential-shaped input and malformed nested data are
rejected. HTTP 404 is unknown, not deletion evidence. Error text and actual values
are not echoed into diagnostic reasons. Revision/hash comparisons do not grant
permission to rewrite the resource.

Default limits: 20 resources, 3 rounds (2–10 supported), 0.2-second inter-round pause,
5-second socket timeout, 60-second overall cooperative budget, 400 request ceiling and
2 MiB body ceiling. These are implementation bounds, **not government-mandated
thresholds**. Remaining read time is applied to the live TLS socket, including
Connection:close responses. The operating system's hostname-resolution call is
not forcibly interrupted by that budget; use approved DNS and an execution-level
deadline for native runs. A slow-body regression proves the response-read budget,
not all resolver failure behavior. The vSphere history profile uses a 120-second
transport budget with its additional documented page/entry bounds.

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
