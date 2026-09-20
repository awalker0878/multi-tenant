# First-site commissioning and live qualification

The documented first path is OpenStack, internal IPv4, two tenants with OZ/RZ
domains, Ubuntu 24.04 guests, GitLab state, NetBox IPAM, the provider Linux edge,
SSH CA identity, TLS logging and restic file recovery. These are reference product
decisions, not evidence that any service or platform is installed. Actual site
endpoints, supported distribution/version, hosts, images and custody cannot be
derived from the symbolic examples. Keep these values in private operator inputs.

## Execute the vertical path

1. Complete the [site-input decision record](../native-reference/site-inputs.md)
   and the selected distribution's installation/adoption MOP. Record physical
   compute/storage/fabric failure domains, project entitlements, quotas, native
   RBAC, encrypted volume types, image provenance, and accepted provider-edge
   attachments. Match the installed release to the pinned provider and API
   contracts. Do not populate accepted indexes before independent acceptance.
2. Commission the recoverable runner and actual GitLab HTTP state/lock service.
   Exercise conflicting writers, access denial across scopes and independent
   state recovery. Protect the private executor ledger and trust/credential
   assets. A lost ledger is a reconciliation hold, not a new operation number.
3. Commission the selected NetBox, authoritative DNS, resolver/time, SSH issuer/revocation, logging,
   package and backup services. Confirm scoped permissions, TLS identity and
   recovery custody. Capture real IPAM reservation/confirmation receipts before
   assigning addresses. Compute capacity reservations remain a separate native
   integration and must be controlled by the site operator.
4. Create the two-tenant prepared fixture with reviewed saved plans. Preserve
   scope-specific outputs and successful receipts. Bind Neutron observations to
   the accepted project and resources; collect Nova/Cinder/Glance identity,
   placement, attachment and image observations. Hold on any mismatch/unknown.
5. Follow [OpenStack bootstrap](openstack-bootstrap.md): accept the deny boundary
   and exact provider service paths, transition domain and workload scopes,
   then repeat native observations. Generate pinned guest access from successful
   workload outputs. Apply the guest baseline/services, rerun for convergence,
   and perform check mode with known drift. Verify logs at the real collector,
   certificate issuance/revocation and successful encrypted captures.
   Confirm native address ownership before the [NetBox-to-DNS handoff](netbox-dns.md).
   Keep independent forward/reverse receipts and verify required resolver/secondary
   propagation. A shared file lock does not replace actual service writer exclusion.
6. Run [campaign v2](target-qualification.md) against the actual guest and native
   targets. Use positive controls around every expected denial. Correlate results
   with enforcement counters and tenant-delegated mutation tests. Independently
   accept readiness before requesting an exact expiring active edge policy.
7. Execute the approved live exercises below, retaining timestamps, exact source
   and input hashes, before/after native observations, healthy controls and
   application-owner results. Failed, interrupted or ambiguous checks require
   withdrawal and reconciliation. Requalification follows every repair.

## Live exercises and closure evidence

Each fault must have a site-specific MOP, exact assets, blast radius, owner,
maintenance budget and already authorized withdrawal/recovery actions. This
repository does not choose a physical switch, host or storage controller to stop.
The read-only campaign collects evidence around the site owner's native action.

| Exercise | Required observation | Closure requirement |
| --- | --- | --- |
| Edge controller loss, reboot and failover | New and established sessions; owned deny boundary before interfaces forward; surviving edge capacity; independent monitoring | No unapproved exposure during loss/restart, accepted recovery timing and actual HA ownership. Kernel lease expiry alone does not qualify reboot or HA |
| Compute failure / rescheduling | Actual Nova hosts/AZ, approved spare capacity, retained Cinder attachments, guest machine/key identity and app health | Placement and separation stay within accepted host sets; no duplicate writer or data loss beyond the declared offer |
| Storage/key-service interruption | Native task completion, encrypted volume identity, attachment consistency, independent key recovery and application state | No guessed completion or automatic recreate after timeout; observed native outcome and data-owner acceptance |
| Tenant-delegated security mutation | Attempts under actual delegated credentials to alter groups, default egress, port security, address pairs, provider attachments and placement | Native denial/mandatory enforcement plus healthy tenant-service controls; provider-token tests cannot substitute |
| East-west and cross-tenant traffic | Same-subnet, cross-domain and cross-tenant cases, reply paths and edge-bypass paths with service controls | Mandatory native policy enforces every offered boundary, including paths that do not traverse the Linux edge |
| Independent recovery | New isolated recovery host, independent credentials/catalogue/key custody, encrypted restore, exact file hashes, application consistency and health | Measured end-to-end application RPO/RTO meet the declared offer; file restore duration alone is insufficient |
| Withdrawal and uncertain outcome | Edge withdrawal, existing-session denial, Terraform prepared transitions, retained disks, native IDs and pending tasks; [owned DNS withdrawal and current IPAM cleanup gates](netbox-dns-retirement.md) | Confirmed closed exposure, preserved data, reconciled tasks; lost/partial DNS cleanup holds IPAM retirement; release IPAM/DNS/capacity only under the separately accepted reuse procedure |

For recovery, use [restic capture/restore](restic-recovery.md), then collect
campaign v2 observations on the separately owned recovery workload. Source and
recovery IDs are distinct; construct a new recovery-scope inventory, manifest and
authority. Do not rewrite a source receipt to make it describe the recovery VM.
The application owner supplies consistency/export and recovered-service checks.

Record accepted results using the existing [native reference campaign](../native-reference/campaign.md)
and [acceptance gates](acceptance.md). Attach failed attempts and resolutions as
well as successful evidence. Repeat the declared offer on VMware/NSX and Nutanix
using the controls below once their remaining integration prerequisites are met. A qualified first
OpenStack site does not qualify those platforms or any public/dual-stack offer.

## VMware and Nutanix follow-on commissioning

The [restricted lifecycle executor](platform-lifecycle.md) now supports exact
NSX/Flow domain bootstrap/withdrawal and AHV workload power/NIC transitions. They use
the reviewed saved-plan process, prior successful native IDs and retained-data
guards. Neither creates a site inventory or establishes effective native policy.

| Platform | Implemented control | Required before a live campaign |
| --- | --- | --- |
| VMware/NSX | Segment ON plus exact IPv4 TCP/UDP exceptions before mandatory dual-family drop; withdrawal returns OFF plus sole drop; vSphere VM/task readback in v5, selected NSX portgroup/segment associations in v6 and port occupants in v7 | Qualify the installed attachment profile, image initialization, DFW priority/membership/exclusions, all enforcement points and same-host paths; actual task/placement/storage evidence and operation-wide fenced reconciliation |
| Nutanix | Existing VM ON/NIC connected, or OFF/disconnected with disks retained; exact owned Flow service exceptions/withdrawal; AHV/network/Flow readback in campaign v4 | Accepted native Flow semantics/precedence and project/category/placement/storage, image initialization and actual network/VM/Flow task evidence; native withdrawal and recovery qualification |

Keep VMware domain and workload state ownership separate. The pinned vSphere
provider's power state is computed, and a clone may already be powered on in the
quarantined domain. A domain withdrawal is not proof that the VM is off. A future
vSphere power writer needs explicit ownership and native fencing; current readers
cannot replay, cancel or clear a held operation. Nutanix domain and VM transitions
are separate applies: enable only independently accepted restricted service paths,
then collect native observations and controlled guest evidence. No cross-scope
atomicity or Flow enforcement is inferred from a successful Terraform apply.

For the optional [AHV VM/task profile](nutanix-vm-task-readback.md), establish
installed VMM v4.2 and Prism v4.3 support and read-role visibility. Capture original
VM power/reconfiguration task IDs, native operation labels, parent/child and entity
sets, expected VM revisions and the actual attempt interval. Qualify these cases:

| Native case | Required result |
| --- | --- |
| Successful root and all recorded children, independently accepted VM state | Stable matching evidence permits review only; preserve the external fence and quarantine |
| Matching VM with pending/failed child or missing task | Hold; never replay to obtain a cleaner result |
| Unlisted entity, truncated child list or unsupported batch shape | Hold for complete native-owner investigation |
| VM placement, NIC/disk identity or revision changes during collection | Hold and preserve the original data/ownership trail |
| Another writer or later operation exists outside the recorded graph | Independent fencing and operation-wide reconciliation remain mandatory; this profile cannot detect all such work |

Exercise offline witness review and v3/v4 campaign collection with those native
records. A simulated fence record cannot close the cross-writer fencing gate.

For the separate [AHV activity profile](nutanix-vm-activity-readback.md), qualify
the exact installed OData affected-entity/status/completion predicate, ascending
task-ID ordering, filtered totals, retention and observation-role visibility.
Include tasks owned by other scoped writers. Unsupported or partially visible
collections must hold; changing the query or removing coverage needs a separately
reviewed profile. Extend commissioning with these cases:

| Native case | Required result |
| --- | --- |
| Pending task started before the interrupted attempt, or separate task completed after it | Visible activity holds despite matching recorded tasks and VM state |
| Shared task affecting multiple accepted VMs | Every VM query contains the same complete native witness; aggregate limits still apply |
| Multiple pages, truncated page, changing count, duplicate/out-of-order row or rejected filter | Only complete stable bounded traversal can match; all uncertain coverage holds |
| Task-list witness differs from direct task GET, or work appears during VM sampling | Hold and retain both witnesses for native-owner investigation |
| Actual saved power/NIC plan with changed disk, MAC, placement or unknown configuration | Held-attempt review refuses contradictory or incomplete bindings |
| Transition expired after the immutable attempt | Historical review may proceed only if it was valid at attempt time; prepare/apply still reject expired authority |

Exercise the [AHV held-attempt reviewer](terraform-recovery.md) with actual sealed
bundles, durable attempt records and independent native expectations. Confirm
that every result preserves the original ledger bytes and grants no replay or
activation authority. Supply genuine current fencing/quarantine evidence before
sampling; this procedure does not create a native writer-exclusion mechanism.

For [campaign v6](vmware-network-binding.md), accept the actual Local Manager
segment/realized-switch and vCenter distributed-portgroup/switch response shapes,
native IDs/revisions and both observers' RBAC visibility. Use original private
domain outputs and workload inputs, and retain their independently accepted
provenance. Qualify the mapping for every offered member/domain, including:

| Native case | Required result |
| --- | --- |
| NIC moved to another owned domain's portgroup | Hold despite both domains being owned and their policies matching |
| Same display name on a different switch/portgroup | Hold on native backing identity mismatch |
| NSX segment points to a different realized logical switch | Hold on the cross-system UUID mismatch |
| Stale portgroup revision, missing DVS reference or changed mapping during sampling | Hold; obtain current accepted expectations and recollect |
| Missing, duplicate, paginated or failed NSX realization | Hold for native-owner investigation |
| Opaque/standard backing, multiple enforcement points or unsupported native shape | Profile refused; qualify a separate supported realization |

For [campaign v7](vmware-network-binding.md#campaign-v7-bind-the-observed-port-occupant),
also accept exact native port keys, connection cookies, VM/NIC connectees, proxy
hosts and selected runtime state. Qualify the installed VI JSON version and
scoped `System.Read` visibility for the fixed `FetchDVPorts` POST. Exercise:

| Native case | Required result |
| --- | --- |
| Reused port key with a different VM/NIC or connection cookie | Hold despite a matching switch and portgroup |
| VM migration changes the serving host or attachment | Hold against old expectations; verify the native outcome before accepting current evidence |
| Blocked, disconnected or conflicting port | Hold; do not filter inactive ports out of the query |
| Observer cannot see the connected VM, cookie or selected runtime fields | Hold; no default identity or successful empty result |
| Missing, extra or duplicate port rows | Hold without broadening the query |
| Attachment changes between port and VM observations | Stop collection and retain containment |

These fixtures still require actual native commissioning. Dynamic group membership,
DFW exclusions/precedence, same-host bypass and real allowed/denied traffic remain
separate checks. Port link/occupant evidence does not establish isolation, HA or
writer exclusion. Do not downgrade a failed attachment campaign to v6/v5.

For the vSphere task-tree profile, accept native task-history visibility,
retention, supported ancestry/operation shapes and session-collector permissions
on the installed tuple. Exercise missing/extra children, incomplete pages and
collector cleanup failure. Bind interrupted existing-VM attempts through the
[recovery reviewer](terraform-recovery.md); it preserves the original ledger hold.
Establish actual native writer exclusion and quarantine before collecting recovery
readback. A local lock or later verification record cannot supply that exclusion.

For held vSphere configuration attempts, collect both VM activity and native
port-attachment reports under the same verified controls. Qualify actual pinned
provider disk/NIC fields against native responses for the current one-controller
boot/optional-data disk and powered-on single-vmxnet3 layout. Exercise:

| Native case | Required result |
| --- | --- |
| Disk UUID, device key, datastore, VMDK path, size or SCSI slot differs from the saved plan | Hold even if VM UUID and completed tasks match |
| Snapshot parent, shared disk, missing backing flags, unknown identity or unsupported controller layout | Hold; no assumed default or data adoption |
| Planned network MoID differs from native portgroup key | Resolve through accepted native portgroup/switch evidence; never assume equal strings |
| NIC key/MAC, port occupant, cookie or serving host differs | Hold; do not reassign expected identities to obtain a match |
| Shared portgroup contains an extra/unassigned selected port | Refuse incomplete or extra attachment coverage |
| Matching VM report collected after fencing but attachment report collected before it | `HOLD_NETWORK_NOT_UNDER_CONTROLS`; resample attachments under current controls |
| Old report without VM snapshot or network attachment witnesses | Refuse review; collect new evidence |
| Matching second VM read follows a differing first read, or a runtime question blocks execution | Hold and preserve native-owner investigation evidence |

Verify immutable ledger preservation for every outcome. Disk retention flags and
matching policy IDs do not prove application recovery, SPBM compliance or native
encryption; qualify those separately. These checks do not add power control,
state adoption or a native writer fence.

Existing-VM receipt review now requires the separate
`vsphere-vi-json-8.0.3.0-vm-task-activity` profile. Qualify its exact VM/`self`
scope, pending-state query without a time cutoff and completion-time window
beginning at the immutable attempt start. Keep user/chain filters absent. Exercise:

| Native case | Required result |
| --- | --- |
| Separate unrecorded root task on the same VM | Hold, even when known tasks and VM configuration match |
| Task queued before the attempt and still running | Visible pending task; hold |
| Task queued before the attempt and completed afterward | Visible completion; hold |
| Task moves from pending to completed between the two queries | Duplicate/changed evidence holds; recollect only under established exclusion |
| Missing records, exhausted pages or failed collector cleanup | Hold; do not downgrade to a narrower profile |
| Shortened/shifted activity window or older known-task-only profile | Held-attempt packet refused |

Independently establish native RBAC/history visibility and retention; the observer
cannot distinguish a silently hidden task from a genuinely absent task. Tasks on
other entities, synchronous operations without tasks and future submissions remain
outside this scan. Complete operation coverage and actual writer exclusion stay
separate acceptance requirements. The clone-tree-only profile remains narrower;
use the separate clone activity profile below for source/destination scans.

For template cloning, capture the installed platform's native `TaskInfo` shape
and description, accepted source MoID/BIOS UUID/instance UUID/revision, original
request/task trail, and exact returned destination MoID/UUID. Validate the
[clone-tree profile](vsphere-readback.md) on a restricted authorized fixture:

| Native scenario | Required observation |
| --- | --- |
| Clone finishes while destination child work remains | Pending child prevents completion review |
| Result VM, source identity or template revision differs | Uncertain/different evidence keeps the operation held |
| Child is absent from accepted scope or history is incomplete | Coverage holds; investigate native ownership rather than guessing an ID |
| Saved CPU/memory plan differs from expected VM configuration | Existing-VM recovery packet is refused |
| Clone completed after a lost provider reply | Preserve data and the ledger; independently reconcile created resource, state ownership and every follow-on task |

Retain real results, including unsupported task types and omission semantics.
Synthetic successful reports must not populate the site's acceptance record.
The clone observer does not implement creation adoption or close power fencing.

Qualify `vsphere-vi-json-8.0.3.0-clone-task-activity` before relying on its combined
source/destination observations. Capture real native attribution, including the
source clone root, returned destination and any child operations. Establish the
actual observation role's visibility and retention on **both** objects, and accept
the exact attempt window. Shared-template ownership and fencing must be covered
by their responsible native owner; tenant-scoped authority alone is insufficient.

| Native scenario | Required result |
| --- | --- |
| Separate clone from the same template | Extra source task holds even if the selected result VM matches |
| Old source task remains pending, or finishes after the attempt start | Visible in the corresponding query; retain the hold |
| Result VM has separate power/reconfiguration work | Hold on the combined task-set difference |
| Source root hidden/expired, or a source/result query is omitted | Missing coverage holds; never treat it as a successful empty scope |
| Accepted clone work belongs to the source and the destination query is empty | Empty query must still be collected and checked against the exact accepted task set |
| Shared template used for several accepted destinations | Query it once while retaining every destination and clone result binding |
| Source page/cleanup fails or aggregate budget is exhausted | Stop collection; preserve containment and the ledger |

Recompute offline witnesses and test the profile with the chosen campaign version.
Matching activity cannot substitute for fencing/quarantine evidence or authorize
state adoption. Do not narrow filters or downgrade profiles after a hold.

Retain the exact task trails, native revision/ETag evidence, failed observations,
healthy denial controls and accepted cross-system bindings. Perform actual HA,
same-host/bypass/security, withdrawal and application-consistent recovery tests
on the intended site. Current fixtures and provider mocks do not close those gates.

## Flow task/activity and held-domain review qualification

Qualify the [Flow activity profile](nutanix-flow-activity-readback.md) independently
of the AHV profile, using actual policy task IDs and labels from the writer trail.
Confirm microseg v4.2/Prism v4.3 compatibility, exact entity/status/completion filter
support, `extId` ordering, filtered totals/page completeness, cross-writer RBAC
visibility and retention. Prove that the installed task graph covers only the
selected policy set; category/VPC/VM side effects need separate reconciliation.

| Native case | Required observation or hold |
| --- | --- |
| Successful recorded update with stable exact policy and ETag | Two stable matching rounds; no enforcement or activation claim |
| Recorded child pending, failed, missing, truncated or foreign | Preserve pending/failure/uncertain hold |
| Old pending task or unrecorded recently completed work | Additional activity holds even when the reviewed policy matches |
| Hidden/expired activity, unsupported query or inconsistent totals/order | Keep the target unqualified; never substitute snapshot-only recovery |
| Alternate native selector outside the expected projection | Policy shape holds; rehashed MATCH summary cannot remove the failed verdict |
| Held bootstrap or service withdrawal | Bind actual sealed transition/plan/attempt and known retained deny IDs; preserve every ledger byte |
| New computed service-rule ID | Original plan explicitly marks only that new ID unknown; accepted policy/service semantics and all retained IDs still match |
| Missing accepted native fence or live quarantine proof | Keep recovery held and establish controls through their owners |

Use controlled guest traffic with healthy controls to qualify allowed services,
cross-domain and same-host denials, policy precedence and withdrawal. Exercise
lost replies and late tasks under the accepted native fencing mechanism. Compare
actual generated rule IDs/provider defaults to the saved plan and retain the
private review packet. Synthetic TLS/plan tests do not supply these results or
prove HA, retained-data/application recovery or production readiness.
