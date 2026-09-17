# vsphere-workload

Provider interface pin: `hashicorp/vsphere` `= 2.12.0`. This is not an installed compatibility decision.

The vSphere resource does not expose a writable power_state or start_connected option in the checked interface. This module does NOT invent those fields or promise powered-off staging. It clones onto an already accepted, mapped NSX quarantine segment and may power on. Before running, the NSX owner must independently verify DROP policy, membership, exclusions, segment isolation and any non-IP paths. Requires a supported single-disk, single-vmxnet3-NIC template and matching firmware/SCSI/disk provisioning; other template layouts are outside this increment. keep_on_remove retains disks but is not a recovery guarantee; retained files need a disposal owner.

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
| `resource_pool_id` | `string` | `required` | Accepted zone-eligible resource-pool managed object ID |
| `datastore_id` | `string` | `required` | Accepted datastore managed object ID |
| `quarantine_network_id` | `string` | `required` | vCenter network ID mapped to the accepted NSX quarantine segment |
| `template_uuid` | `string` | `required` | Approved single-boot-disk single-NIC template UUID |
| `guest_id` | `string` | `required` | Guest OS ID matching the approved template |
| `scsi_type` | `string` | `required` | SCSI controller type matching the template |
| `firmware` | `string` | `required` | Template firmware |
| `storage_policy_id` | `string` | `required` | Accepted storage policy ID |

## Outputs

`vm_id`, `observed_power_state`, `delivery_state`.

Output IDs and the static delivery-state label do not establish native readiness, test results or authorization.
