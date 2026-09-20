# VMware and Nutanix restricted lifecycle

The pinned providers expose different controls. Nutanix VM bootstrap requests
ON and connects the existing NIC. Withdrawal requests OFF and disconnects it.
VMware domain bootstrap connects the owned NSX segment and inserts exact IPv4
TCP/UDP exceptions before the mandatory dual-family drop; withdrawal restores
the sole drop and disconnects the segment. The vSphere provider may power on a
clone and exposes power state as computed, so no writable power switch is added.

Terraform remains the writer for these existing native objects. Native ownership,
effective policy and guest initialization must be independently accepted. The
Nutanix VM transition alone cannot override its domain's deny policy. The owned
Flow policy now supports exact IPv4 TCP/UDP service exceptions in bootstrap and
removes them on withdrawal. Both original deny rules, ENFORCE, hit logging, the
owned category and VPC scope are retained. Commissioning must prove the actual
installed policy semantics, precedence and service paths. Do not edit
the Terraform-owned policy through a competing writer. No external attachment,
route advertisement, HA placement, image credential or site inventory is inferred.

## Exact saved-plan contract

`tools/lifecycle_transition.py` creates a `hosting-platform-transition/1` record
from a successful private execution completed within 24 hours. Supported scopes
are Nutanix domains/workloads and VMware domains. Existing OpenStack transition records
remain accepted by the saved-plan executor through the same validation dispatch.

Copy the previous run's inputs. Keep the allocation, placement, image, hardware,
endpoint and member inputs identical. Change only each member's `lifecycle_stage`,
`bootstrap_acceptance_ref`, applicable `bootstrap_rules`, and the root change
reference. Every member must use the same target stage. Bootstrap rules have
`direction` (ingress/egress), `protocol` (tcp/udp), one integer `port` and one
unicast `remote_ipv4`; their scope is the whole owned domain group.

The owner-only acceptance file has `valid_from`, `valid_until` (at most one hour)
and `acceptance_refs` with `native_boundary`, `service_paths`, `image_bootstrap`
and `withdrawal`. These reference independently accepted site records; they are
not cryptographic signatures or an approval service.

```sh
python tools/lifecycle_transition.py --prior-run /private/prior-run \
  --inputs /private/bootstrap-inputs.json --acceptance /private/acceptance.json \
  --stage bootstrap --output /private/transition.json
```

Use the [saved-plan process](terraform-execution.md), passing
`--transition /private/transition.json` to preparation. The record is sealed in
the bundle, revalidated against exact inputs before apply, and expires alongside
the separately issued apply authority. Resource addresses and native IDs/paths
must match the prior outputs. Unknown security values, drift, creation, deletion,
replacement, adoption, membership changes and unrelated native updates block.

For NSX, the full ordered rule list must match the requested services and terminal
drop. No exclusion, alternate scope, protocol expansion or hidden nonempty rule
selector is accepted. Segment changes are restricted to connectivity. For AHV,
only power and the existing NIC's connection flag may change; disks, addressing,
cluster/project/category and other VM fields are held constant.

For Flow, only the exact owned policy's rule list and computed update metadata
may change. The prior two deny rules must remain unchanged. Added application
rules use the owned category, one /32 peer and one TCP/UDP port, with no all-protocol
allow, alternate category/address/entity group, service insertion or unrelated
native change. Bootstrap without a valid lifecycle record is blocked by plan
review. Withdrawal keeps the same policy ID and restores its original deny pair.

The reviewer recognizes the pinned NSX provider's computed `nsx_id` and empty
service defaults. Nonempty alternate protocol entries still block. Known rule
sequence numbers must agree with the reviewed order; omitted/zero numbers are
assigned by the provider and must be checked in the native policy observation.

## Native hold points

Before bootstrap, accept native Flow/DFW precedence, membership and exclusions,
same-host paths, actual guest addressing/identity, placement/storage and the
provider edge's limited services. Prepared Terraform outputs do not prove these
properties. After apply, read actual power/NIC or NSX realization, then execute
healthy-control traffic tests and guest convergence before activation.

For NSX use the existing exact-policy observer, including actual rule order,
scope, intent version and every accepted enforcement point. Segment connectivity
OFF alone does not establish same-segment isolation: observe the mandatory DFW
drop and test same-host paths. For Nutanix use [AHV VM readback](nutanix-vm-readback.md),
[Flow readback](nutanix-flow-readback.md) and [campaign v4](target-qualification.md)
alongside actual network/VM task evidence. For VMware use
[vSphere VM/task readback](vsphere-readback.md) and campaign v5, or
[campaign v6/v7](vmware-network-binding.md) for observed NSX-backed portgroup/segment
associations and, in v7, exact port occupants, connection cookies and host/runtime
bindings. These observations cannot resolve an uncertain native operation.
Task profiles check accepted tasks and, where selected, bounded child history or
visible existing-VM activity. The separate clone activity profile scans both the
accepted template and destination for visible pending/late work; it retains source
identity and result/tree checks. These profiles never clear an execution ledger or authorize
replay. The [held-attempt reviewer](terraform-recovery.md)
binds existing-VM observations to the exact saved plan and current durable hold,
comparing supported CPU/memory/topology configuration and holding other updates.
The separate clone-tree profile observes accepted template identity/revision and
the clone's exact result VM without adopting it into state. No live platform is
contacted by provider mocks, synthetic plans or the local HTTPS fixtures.

On failure, withdraw the separately owned edge exposure first. Prepare and review
a fresh transition to `prepared`, keeping the same VM/storage/member inputs.
NSX withdrawal removes inline exceptions, with its mandatory drop retained.
Flow withdrawal removes service exceptions while retaining both deny rules;
the separate AHV workload withdrawal powers off and disconnects the existing NIC.
Read back the final state, including existing-session behavior. These operations
are not atomic across scopes; timeout or partial native outcomes remain held for
reconciliation. Do not delete disks or revert Terraform state to recover data.

Live HA/security/recovery qualification and supported installed tuples remain
required. Follow the [commissioning sequence](site-commissioning.md). Provider
mocks and synthetic saved plans exercise implementation boundaries, not native
enforcement or failure recovery.

Remaining vSphere integration includes a separately fenced, data-preserving
power/guest-bootstrap owner, complete native task coverage beyond the bounded
template-clone/power/reconfiguration/activity profiles, effective per-port/DFW
membership and unsupported network realizations beyond v7's selected attachments, and
operation-wide reconciliation and authorized ledger recovery. The observers and
reviewer do not supply these write/fencing interfaces. Keep the NSX containment and reviewed
operator hold points until those capabilities and their live behavior are accepted.

Interfaces checked against the pinned provider sources:
[Nutanix 2.4.2 VM](https://github.com/nutanix/terraform-provider-nutanix/blob/v2.4.2/website/docs/r/virtual_machine_v2.html.markdown),
[NSX 3.10.0 policy](https://github.com/vmware/terraform-provider-nsxt/blob/v3.10.0/docs/resources/policy_security_policy.md),
[vSphere 2.12.0 VM](https://github.com/vmware/terraform-provider-vsphere/blob/v2.12.0/docs/resources/virtual_machine.md).
