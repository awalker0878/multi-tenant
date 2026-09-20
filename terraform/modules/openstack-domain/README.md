# openstack-domain

Provider interface pin: `terraform-provider-openstack/openstack` `= 3.4.0`. This is not an installed compatibility decision.

Creates new project-owned resources only. Network/router start administratively down; DHCP is deliberately disabled for staging. No external gateway, SNAT argument, floating IP, permissive rule or modification of the project default group is included. DHCP/metadata/approved service activation is a later separately reviewed step. Neutron implicit control-protocol behavior and provider-owned API policy must be tested.

No provider configuration or credentials live in this child module. `prevent_destroy` is a configuration safeguard, not an authorization or backup mechanism; removing configuration can remove that protection. Retirement requires a separately reviewed change. Module outputs are resource identifiers, not acceptance evidence. See [commissioning](../../../docs/COMMISSIONING.md) and the [release guide](../../../Implementation_Execution_Guide.docx).

## Inputs

Native and allocation IDs must come from accepted engineering records. Credentials are root-only.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `tenant_key` | `string` | `required` | Stable tenant identifier |
| `domain_key` | `string` | `required` | Stable domain identifier |
| `allow_restricted_build` | `bool` | `false` | Explicit operator opt-in for an authorized non-production build |
| `test_authorization_ref` | `string` | `required` | Reference to separately issued test-scope authorization |
| `ipv4_cidr` | `string` | `required` | Allocated canonical IPv4 domain prefix |
| `gateway_host_number` | `number` | `1` | Usable host offset for the native gateway |
| `project_id` | `string` | `required` | Keystone project ID matching the execution credential scope |

## Outputs

`network_id`, `subnet_id`, `router_id`, `security_group_id`, `delivery_state`.

Output IDs and the static delivery-state label do not establish native readiness, test results or authorization.
# Restricted bootstrap lifecycle

Defaults keep the network and router down. `lifecycle_stage = "bootstrap"`
requires `bootstrap_acceptance_ref` and is a separately reviewed non-production
transition. `bootstrap_rules` adds only named IPv4 /32 TCP/UDP service tuples to
the provider-owned group; default egress stays removed. Keep the rule map when
returning to `prepared`: interfaces go down and rule identities remain owned.
Rule deletion is prevented until a separate retirement design is accepted.
The normal restricted-plan reviewer still blocks exposure without the dedicated
transition contract. Native mandatory-policy ownership and actual routing must
be independently accepted before a transition.
