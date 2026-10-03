# NSX domain lifecycle observation and held review

`provisioner/execution/nsx_domain_observe.py` provides the explicit
`nsx-local-policy-v1-domain-lifecycle` profile for existing VMware domains. It
observes accepted Local Manager object paths with GET requests only. It adds no
writer, native fence, task inventory, state adoption or activation authority.
The [disabled example](../../../examples/nsx_domain_observation.json.example)
contains synthetic identities and expectations; replace them only from accepted
engineering and native-owner records. Never populate an expected baseline from
the unreviewed response being tested.

`provisioner/execution/nsx_domain_binding.py` then binds the observed domain intent to exact
owned outputs and provider inputs. Binding establishes record consistency only:
it does not authenticate ownership, prove packet enforcement, renew apply
authority or release a held operation.

## Required observation scope

Use the common [native manifest envelope](../../NATIVE_READBACK.md) with platform
`nsx`, the original operation ID and portable tenant/WSD, the accepted NSX origin,
engineering/target bindings and no task section. Each resource has `kind`, exact
`path`, `expected` and `realization`. The latter records an independent
`intent_version` and exact enforcement-point paths; an intent version is not
assumed equal to a configuration revision.

Supply exactly four distinct owned resources per domain, at most five domains
per manifest. Shared or omitted objects are refused. Larger scopes require an
engineered bounded extension; do not drop members from a held attempt.

| Object | Required selected fields beyond identity/revision, display name and empty tags |
| --- | --- |
| Tier-1 | Empty Tier-0 path and advertisement type/rule lists |
| Segment | Owned Tier-1 path, accepted transport zone, gateway subnet and connectivity/uRPF configuration |
| Group | One `PathExpression` selecting exactly the owned segment; no extended expressions |
| Security policy | Exact group scope, category, sequence, stateful/TCP-strict/locked flags and complete ordered rule list |

Rules include native ID/path/type/revision/rule ID, display name and sequence,
action/direction/address family, enabled/logged flags, source/destination lists
and exclusions, services, inline entries, profiles and scope. This profile permits
only inline TCP/UDP entries with one destination port and no source-port selector.
Held review additionally requires the exact sealed services and terminal drop.

Both full configuration responses are checked for unsupported fields before
projection. Only enumerated attribution metadata and explicitly inactive defaults
are omitted. Additional DHCP/bridge/pool behavior, alternate group/rule selectors,
deleted/system-owned objects and unsupported shapes hold. Required fields must be
present even when empty. An installed API that omits them needs a separately
reviewed normalization; do not invent values to make the report pass.

Configuration reads bracket each realization request. Offline review rechecks
both selected snapshot hashes, identity/revision and the bounded realization
witness, including version, publication and complete enforcing-system span.
Two identical completed rounds are required. Pending, failed, changed, foreign or
unknown observations retain distinct holds. Domain reports also carry both
native-shape verdicts; missing/false verdicts invalidate offline review.
These records are consistency evidence, not collector signatures or native
authorization. Private custody and independent controls remain prerequisites.

## Collection and held-plan review

Validate without contacting an endpoint:

```sh
python3 -m provisioner.execution.nsx_domain_observe /private/operator/nsx-domain.json
```

After the responsible owners establish real scoped fencing and quarantine,
collect current observations with independently injected `NSXT_USERNAME` and
`NSXT_PASSWORD`, accepted TLS trust, explicit enabled contact and a new output:

```sh
python3 -m provisioner.execution.nsx_domain_observe /private/operator/nsx-domain.json \
  --read-authorized-target --expected-origin https://accepted-nsx.example.invalid \
  --ca-file /private/operator/site-ca.pem \
  --output /private/operator/nsx-domain-report.json
```

The documentation origin is intentionally non-contactable. Use the actual
accepted origin in the private manifest and command. Credentials and native
evidence must stay outside the repository.

For a held `vmware-wsd-domains` attempt, follow
[Terraform recovery review](terraform-recovery.md). The original sealed transition
must contain prior Tier-1, segment, group and policy paths, unchanged member
allocation/provider inputs and the supported bootstrap/prepared target. The saved
plan must cover exactly those four resources per member with existing identities.
Tier-1 and group must be resolved no-ops. Segment connectivity and the exact policy
rule list are the supported changes. Unchanged but unobserved alternate behavior,
unknown security values, imports, moves, creates, replacements and deletes hold.

Retained rule IDs must be known and unchanged by name, including the terminal
drop when its list position changes. New rule IDs may be unknown only where the
original saved plan explicitly marks them computed; current accepted native IDs
and semantics are still required. Known paths/revisions/numeric rule IDs and
effective sequence numbers must agree. Unresolved retained IDs need separate
native-owner reconciliation; do not edit the sealed plan. The reviewer preserves
every ledger byte and all mutation flags remain false.

The selected conversions follow NSXT provider 3.10.0's
[rule construction](https://github.com/vmware/terraform-provider-nsxt/blob/v3.10.0/nsxt/policy_common.go),
[empty path-list conversion to ANY](https://github.com/vmware/terraform-provider-nsxt/blob/v3.10.0/nsxt/policy_utils.go),
[segment mapping](https://github.com/vmware/terraform-provider-nsxt/blob/v3.10.0/nsxt/segment_common.go)
and [policy reads](https://github.com/vmware/terraform-provider-nsxt/blob/v3.10.0/nsxt/resource_nsxt_policy_security_policy.go).
Installed API omission/default semantics, generated/retained rule behavior and
realization attribution still need native qualification.

## Combined domain and logical-switch observation

`provisioner/execution/nsx_domain_switch_observe.py` uses the explicit
`nsx-local-policy-v1-domain-switches` profile. Keep all four owned resources,
strict full-response checks and realization expectations above. Add the accepted
`logical_switch` object from the [segment profile](vmware-network-binding.md#nsx-segment-realization-identity)
to every segment and no other object. The [disabled combined example](../../../examples/nsx_domain_switch_observation.json.example)
can be validated without contact:

```sh
python3 -m provisioner.execution.nsx_domain_switch_observe /private/operator/nsx-domain-switches.json
```

Collection uses the same explicit contact, origin, credentials, CA and private
output controls as the domain command. Each round reads realized switches, all
domain objects/configuration/realization, then switches again. Both switch reads
retain bounded selected witnesses and empty-alarm verdicts for offline replay;
unsupported full domain shapes still hold. This does not add NSX task coverage.

[Campaign v8](target-qualification.md#campaign-v8-bind-full-domain-intent)
composes these observations with vSphere port and VM evidence and guest probes.
It additionally binds all owned domain paths and requested service semantics to
original private inputs/outputs. The domain-only profile remains the contract
for held Terraform domain review; neither profile silently substitutes for the
other.

## Independent work that remains

This profile covers four selected object snapshots, not asynchronous work across
all entities or an atomic cross-object transaction. It does not enumerate locale
services, route tables, external attachments, effective group members, DFW
exclusions/precedence, or rules on every ESXi/Edge node. It does not prove packet
enforcement, HA, storage or useful-data recovery. The separate campaign v6/v7
segment/switch/port profiles keep their existing contracts; this domain profile
cannot replace their attachment or healthy-control traffic evidence. Campaign v8
explicitly includes those checks alongside the combined domain/switch profile.

Qualify the [site scenarios](site-commissioning.md), actual cross-writer exclusion
and current quarantine before recovery review. Native late effects, task coverage,
state reconciliation and separately approved forward action remain open. A
matching report or review packet does not make the platform production-ready.
