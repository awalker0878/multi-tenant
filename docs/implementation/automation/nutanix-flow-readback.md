# Nutanix Flow policy readback

`tools/nutanix_flow_observe.py` reads exact policy IDs through microseg v4.2. It
compares a reviewed native snapshot and strong ETag, then independently checks the
restricted policy shape. A matching snapshot is not proof of enforcement,
realization, task completion, or readiness to activate.

The profile is `nutanix-microseg-v4.2-policy-snapshot`. Use the common Nutanix
manifest envelope described in [AHV readback](nutanix-vm-readback.md), without a
`task`. Each resource has exactly `kind` (`policy`), `ext_id`, `category_id`,
`vpc_id`, `services`, `expected_etag`, and `expected`. IDs are independently
accepted native UUIDs. `services` uses the lifecycle bootstrap rule map: direction,
TCP/UDP protocol, one port, and one remote IPv4 address per named service. Empty
services means the prepared policy with its two retained deny rules.

`expected` is the reviewed API policy object with native rule IDs and direct
camel-case union specifications, not Terraform state. It must contain `extId`,
`$objectType`, `tenantId`, `name`, `type`, `state`, `scope`, `vpcReferences`,
`isHitlogEnabled`, `isIpv6TrafficAllowed`, and `rules`. The validator requires the
owned category, exact VPC, ENFORCE, hit logging, disabled IPv6 bypass, both original
deny rules, and exactly the sorted service rules. Extra address/category/entity
groups, IPv6 selectors, service insertion, wider ports, or alternate rule unions
hold the observation even when omitted from the expected projection. Unsupported
native shapes remain held for engineering review.

Validate without contact:

```sh
python3 tools/nutanix_flow_observe.py /private/site/flow-manifest.json
```

After scoped read authorization, use `--read-authorized-target`,
`--expected-origin`, `--ca-file`, and a new private `--output`. Inject the scoped
reader through `NUTANIX_USERNAME` and `NUTANIX_PASSWORD`. The transport permits
only GETs to `/api/microseg/v4.2/config/policies/{extId}`, checks TLS, refuses
redirects, and uses bounded polling. It never writes policies or discovers IDs.
Reports contain selected digests and mismatch paths, not response bodies.

Provider semantics and wire shapes were checked against the pinned
[Nutanix 2.4.2 provider](https://github.com/nutanix/terraform-provider-nutanix/tree/v2.4.2)
and [microseg SDK 4.2.2](https://github.com/nutanix/ntnx-api-golang-clients/tree/microseg-go-client/v4.2.2/microseg-go-client).
Repository TLS fixtures test serialization and refusal behavior; they do not
qualify an installed Prism/Flow version. Commissioning must still bind policy
ownership and category membership, prove allowed service traffic and cross-domain
denials with healthy controls, test withdrawal, and retain live recovery evidence.

The separate [Flow task/activity profile](nutanix-flow-activity-readback.md) brackets
these policy reads with recorded Prism tasks and visible policy activity. It
supports campaign v4 and held existing-domain lifecycle review. The original
snapshot profile remains task-free. Both profiles now retain selected policy/ETag
hashes and the full-shape verdict for offline consistency checks; older reports
without these witnesses require recollection.
