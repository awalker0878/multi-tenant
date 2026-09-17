# nutanix-domain

Provider interface pin: `nutanix/nutanix` `= 2.4.2`. This is not an installed compatibility decision.

Creates a real VPC, overlay subnet, provider-owned category and scoped enforced policy. No external subnet, route, NAT or allow rule is created. The category must be protected by accepted native RBAC. Native policy precedence, IPv4-only handling and intra-group enforcement need live qualification before any NIC is connected.

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

## Outputs

`vpc_id`, `subnet_id`, `security_category_id`, `quarantine_policy_id`, `delivery_state`.

Output IDs and the static delivery-state label do not establish native readiness, test results or authorization.
