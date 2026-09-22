# Examples and synthetic fixtures

`wd14-routing.json` is the unchanged documentation topology. The offline route
auditor covers both address families; the actual namespace fixture executes only
its IPv4 subset. None of its prefixes are site allocations.

The saved plans named `synthetic_*` are constructed unit-test fixtures, not outputs
from Terraform. Native provider plans cannot be claimed while the engine is absent.

## Portable provisioning reference corpus

`requests/` holds the five reviewed portable requests; `resolved/` holds their
deterministic resolution, placement and desired-state artifacts; `golden/` holds
their environment and conformance documents plus the `digests.json` index. The
`tests/provisioning/end_to_end/test_golden.py` regressions replay all of them. They plan as
`PLANNED_DISABLED_NOT_AUTHORIZED` with `native_contact: false`; see the
[portable provisioning documents](../docs/provisioning/README.md).

`golden/cross-platform.digests.json` records the same portable request realized on
each reviewed platform fixture. Every platform is asked for the identical portable
body; only `spec.platform.preference` differs, so `portable_digest` is shared while
`request_digest` is not. The artifact also stores the per-platform realization
gaps, which is how the VMware boundary (no address on the workload) stays visible
rather than being silently dropped.

`neutron_observation.json.example` and `accepted_route_record.json.example` contain
intentionally unusable placeholders. Populate actual expectations from accepted
engineering and inventory records, never by treating example values as approvals.
Every root's `inputs.tfvars.json.example` is disabled. Credentials must be injected
through the approved execution environment and are not part of these files.
