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
# Restricted Flow service lifecycle

`lifecycle_stage` defaults to `prepared`, preserving the original two deny rules.
Explicit `bootstrap` adds sorted exact IPv4 /32 TCP/UDP service rules for the
owned category and VPC. Both allow modes remain `NONE`; only the selected peer
and port are supplied. Return to `prepared` removes the exceptions and preserves
the baseline/intra-group denies. No external VPC attachment is added.

This follows the pinned provider's selective-subnet acceptance example in
[the 2.4.2 tests](https://github.com/nutanix/terraform-provider-nutanix/blob/v2.4.2/nutanix/services/networkingv2/resource_nutanix_network_security_policies_v2_test.go).
Provider mocks check schema and intended values, not installed Flow semantics.
Native policy precedence, category ownership, paths, task completion and healthy
denial controls must be accepted before using the service. Bootstrap requires
`bootstrap_acceptance_ref`; a reference string is not approval authentication.
