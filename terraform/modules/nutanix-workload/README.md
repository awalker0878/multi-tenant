# nutanix-workload

Provider interface pin: `nutanix/nutanix` `= 2.4.2`. This is not an installed compatibility decision.

Defaults create a VM with owned boot/optional data disks, selected cluster/project/category, an explicitly disconnected NIC and OFF requested state. An explicit `lifecycle_stage = "bootstrap"` with `bootstrap_acceptance_ref` requests ON and connects the single NIC. Returning to `prepared` disconnects it and requests OFF without replacing the VM or disks. Native power/NIC behavior and accepted Flow service policy must be observed independently. The image must already support the accepted address/bootstrap mechanism and operator identity. No backup policy or key-service grant is fabricated. Cluster choice must already enforce the accepted zone/co-residency policy; this module does not install HA placement policy.

No provider configuration or credentials live in this child module. `prevent_destroy` is a configuration safeguard, not an authorization or backup mechanism; removing configuration can remove that protection. Retirement requires a separately reviewed change. Module outputs are resource identifiers, not acceptance evidence. See [commissioning](../../../docs/COMMISSIONING.md) and the [release guide](../../../Implementation_Execution_Guide.docx).

## Inputs

Native and allocation IDs must come from accepted engineering records. Credentials are root-only.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `tenant_key` | `string` | `required` | Stable tenant identifier |
| `domain_key` | `string` | `required` | Stable domain identifier |
| `allow_restricted_build` | `bool` | `false` | Explicit operator opt-in for an authorized non-production build |
| `test_authorization_ref` | `string` | `required` | Reference to separately issued test-scope authorization |
| `workload_key` | `string` | `required` | Owned workload identity |
| `vcpu` | `number` | `2` | Requested guest vCPU |
| `memory_gib` | `number` | `4` | Requested guest memory in GiB |
| `boot_disk_gib` | `number` | `40` | Requested boot disk GiB; must be at least image/template size |
| `data_disk_gib` | `number` | `0` | Owned optional data disk GiB; zero omits |
| `accepted_quarantine_ref` | `string` | `required` | Scoped independently reviewed network/policy/placement handoff reference |
| `cluster_id` | `string` | `required` | Accepted zone-eligible AHV cluster UUID |
| `project_id` | `string` | `required` | Accepted project UUID |
| `storage_container_id` | `string` | `required` | Accepted storage-container UUID |
| `image_id` | `string` | `required` | Approved boot-image UUID |
| `subnet_id` | `string` | `required` | Accepted isolated domain subnet UUID |
| `security_category_id` | `string` | `required` | Provider-owned category UUID from domain handoff |
| `ipv4_address` | `string` | `required` | Reserved endpoint IPv4 address |

## Outputs

`vm_id`, `delivery_state`, `lifecycle_stage`.

`lifecycle_stage` defaults to `prepared`; `bootstrap_acceptance_ref` defaults to
empty and is required for bootstrap. These fields do not authorize a transition;
use a separately reviewed saved plan. Restricted initial compilation cannot set
them to bootstrap. Disk retention remains guarded by `prevent_destroy`.

Output IDs and the static delivery-state label do not establish native readiness, test results or authorization.
