# nsx-domain

Provider interface pin: `vmware/nsxt` `= 3.10.0`. This is not an installed compatibility decision.

Targets NSX Local Manager only, not Global Manager or VMC. Creates a disconnected segment, unconnected Tier-1, segment-membership group and group-scoped Emergency DROP policy. An empty source/destination list means Any within the explicitly scoped group. Segment disconnection is not a same-subnet or non-IP isolation proof. Existing higher-priority policy and DFW exclusions must be inspected before attaching a VM; the sequence is an allocated policy slot, not a universal safe default. No Tier-0/VRF is created.

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
| `transport_zone_path` | `string` | `required` | Accepted NSX Local Manager overlay transport-zone path |
| `quarantine_sequence` | `number` | `required` | Provider-reserved Emergency policy sequence |

## Outputs

`tier1_path`, `segment_path`, `group_path`, `quarantine_policy_path`, `delivery_state`.

Output IDs and the static delivery-state label do not establish native readiness, test results or authorization.
