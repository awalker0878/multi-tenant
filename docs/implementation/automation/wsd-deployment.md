# WSD deployment scopes

The [cluster design](../../engineering/cluster-topology-and-wsd-placement.md) separates provider capacity from a WSD allocation. Terraform now supplies six compositions: domain and workload phases for Nutanix, VMware/NSX and OpenStack. Each invocation owns one tenant/WSD. Running two tenant scopes gives the reference fixture's four OZ/RZ domain instances without sharing their credentials or state.

## Directory and writer boundaries

| Scope | Entry point | State owner |
| --- | --- | --- |
| Nutanix domains | `terraform/stacks/wsd/nutanix/domains` | Tenant/WSD networking authority |
| Nutanix workloads | `terraform/stacks/wsd/nutanix/workloads` | Tenant/WSD compute authority |
| NSX domains | `terraform/stacks/wsd/vmware/domains` | Tenant/WSD networking authority |
| vSphere workloads | `terraform/stacks/wsd/vmware/workloads` | Tenant/WSD compute authority |
| OpenStack domains | `terraform/stacks/wsd/openstack/domains` | Tenant/WSD project networking authority |
| OpenStack workloads | `terraform/stacks/wsd/openstack/workloads` | Tenant/WSD project compute authority |

Security-edge routes and quarantine roots remain under `terraform/stacks/components`. Their owners must not also assign the same resource or field to a WSD state. Platform installation, fabric, shared services, trust and protection are separate commissioning operations, not hidden side effects of a tenant deployment. No selected installer or state-service deployment is supplied until the actual site choices are recorded.

Each composition accepts `tenant_key`, `wsd_key`, disabled-by-default `allow_restricted_build`, `test_authorization_ref`, and a typed `members` map. Domain map keys are native domain identities; workload map keys are native workload identities. Map ordering does not change resource addresses. Empty maps are rejected; this interface is not a retirement mechanism. Required module inputs remain required and primitive lifecycle guards remain in force. Object attributes and stable iteration follow Terraform's [type constraints](https://developer.hashicorp.com/terraform/language/expressions/type-constraints) and [module for_each](https://developer.hashicorp.com/terraform/language/meta-arguments/for_each) semantics.

## Ordered restricted build

1. Select actual supported platform/site/tuple, commissioned cluster capacity and accepted WSD placement. Resolve authoritative reservation/IPAM/DNS and independently owned edge/service dependencies. The repository's empty qualification indexes do not authorize allocation.
2. Assign unique backend addresses and lock endpoints to environment/site/platform/tenant/WSD/phase. Bootstrap the chosen encrypted, versioned state service and demonstrate access separation, locking and restore. Inject provider/backend credentials from private systems. Do not put credentials in backend files, command arguments or committed inputs.
3. Copy the disabled example from the selected domain root into private storage and populate accepted allocations. Initialize the root with its owned backend, create a saved plan and review its exact source, inputs, changes and scope before applying that plan. Save the narrow `terraform output -json` output privately.
4. Observe actual quarantine and placement independently. Terraform completion or a nonempty authorization-reference string does not prove effective policy. VMware clones can power on, so this must precede workload creation.
5. Populate the workload phase using accepted domain outputs and platform placement/image handoffs. Nutanix consumes subnet/category IDs; OpenStack consumes network/subnet/security-group IDs; vSphere requires an independently observed vCenter network ID mapped to the NSX segment, not a guessed conversion from a segment path.
6. Review and apply the separate workload plan. Capture native IDs and reconcile partial/late tasks before retrying any uncertain operation. The native modules preserve restricted state. Guest bootstrap, service enrollment, connectivity activation and retirement require the separate accepted operations in the [backlog](completion-backlog.md).

Outputs contain `scope`, `members` keyed by immutable identity, and `delivery_state`. Scope identifies tenant/WSD/platform/phase. Member outputs preserve each primitive's native IDs and restricted state. Never treat output JSON as native observation or authority to activate.

## Existing resources and state

Moving a component root into `stacks/components` preserves its addresses. Adopting the new WSD composition changes addresses to `module.owned.module.member["identity"].…` and is a separate migration. Back up state, fence all writers, map every old/native/new identity and review an explicit state move or supported import before planning. Do not apply an empty composition state against existing native resources. `prevent_destroy` blocks destructive changes; removing a module from configuration can remove its guard, so a reviewed ownership and retention process remains mandatory. No universal state migration or deletion script is provided.

## Verification limits

The catalogue and engine verifier include every component/composition/root. CI validates schemas and restricted plan-only mocks without native credentials or backend access. Generated composition tests check stable output identities and empty-scope rejection; primitive tests check native quarantine fields. Passing these gates proves source/engine behavior only. Native create/read/replan, interruptions, quotas, survivor capacity, guest operation and useful-data recovery remain target-bound acceptance work.
