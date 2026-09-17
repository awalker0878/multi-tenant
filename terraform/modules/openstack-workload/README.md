# openstack-workload

Provider interface pin: `terraform-provider-openstack/openstack` `= 3.4.0`. This is not an installed compatibility decision.

Uses a separately managed administratively down Neutron port with an explicit group; no instance-level group is substituted. The provider creates the server before requesting shutoff, so a brief initial boot may occur. Isolation relies on the down port and accepted network baseline, not a claim of never executing the guest. Boot/data volumes are separately owned; boot delete_on_termination is false. The provider credential project must match every handoff. Flavor ID is authoritative; the flavor must be checked against the independently accepted demand and scheduler policy. The module does not create or mutate a flavor.

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
| `boot_disk_gib` | `number` | `40` | Requested boot disk GiB; must be at least image/template size |
| `data_disk_gib` | `number` | `0` | Owned optional data disk GiB; zero omits |
| `accepted_quarantine_ref` | `string` | `required` | Scoped independently reviewed network/policy/placement handoff reference |
| `network_id` | `string` | `required` | Accepted quarantine network UUID |
| `subnet_id` | `string` | `required` | Accepted quarantine subnet UUID |
| `security_group_id` | `string` | `required` | Accepted no-user-flow group UUID |
| `ipv4_address` | `string` | `required` | Authoritatively reserved IPv4 address |
| `image_id` | `string` | `required` | Approved Glance image UUID |
| `flavor_id` | `string` | `required` | Approved flavor ID matching requested capacity and placement |
| `compute_availability_zone` | `string` | `required` | Accepted Nova availability zone |
| `storage_availability_zone` | `string` | `required` | Accepted Cinder availability zone |
| `volume_type` | `string` | `required` | Accepted storage/encryption type |

## Outputs

`server_id`, `port_id`, `boot_volume_id`, `data_volume_ids`, `delivery_state`.

Output IDs and the static delivery-state label do not establish native readiness, test results or authorization.
