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
3. Commission the selected NetBox, resolver/time, SSH issuer/revocation, logging,
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
| Withdrawal and uncertain outcome | Edge withdrawal, existing-session denial, Terraform prepared transitions, retained disks, native IDs and pending tasks | Confirmed closed exposure, preserved data, reconciled tasks; release IPAM/DNS/capacity only under the retirement procedure |

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
| VMware/NSX | Segment ON plus exact IPv4 TCP/UDP exceptions before mandatory dual-family drop; withdrawal returns OFF plus sole drop; vSphere VM/task readback in campaign v5 | Independently observed NSX/vCenter network binding, image initialization, DFW priority/membership/exclusions, all enforcement points and same-host paths; actual task/placement/storage evidence and operation-wide fenced reconciliation |
| Nutanix | Existing VM ON/NIC connected, or OFF/disconnected with disks retained; exact owned Flow service exceptions/withdrawal; AHV/network/Flow readback in campaign v4 | Accepted native Flow semantics/precedence and project/category/placement/storage, image initialization and actual network/VM/Flow task evidence; native withdrawal and recovery qualification |

Keep VMware domain and workload state ownership separate. The pinned vSphere
provider's power state is computed, and a clone may already be powered on in the
quarantined domain. A domain withdrawal is not proof that the VM is off. A future
vSphere power writer needs explicit ownership and native fencing; current readers
cannot replay, cancel or clear a held operation. Nutanix domain and VM transitions
are separate applies: enable only independently accepted restricted service paths,
then collect native observations and controlled guest evidence. No cross-scope
atomicity or Flow enforcement is inferred from a successful Terraform apply.

Retain the exact task trails, native revision/ETag evidence, failed observations,
healthy denial controls and accepted cross-system bindings. Perform actual HA,
same-host/bypass/security, withdrawal and application-consistent recovery tests
on the intended site. Current fixtures and provider mocks do not close those gates.
