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

`golden/cross-platform.digests.json` records the full reference-request x platform
matrix: every one of the five reviewed portable requests against each of the three
reviewed platform fixtures, with no cell omitted. A compatible cell is realized and
stores its deterministic request, resolution, placement, desired-state, environment,
plan and manifest digests plus its provider-native stack root and realization gaps. A
cell that is intentionally incompatible — the request selects a different platform
than the reviewed fixture represents — stores the explicit refusal (code, JSON path,
status and reason) instead of being dropped. Each request is planned against each
fixture with only `spec.platform.preference` selected, so every platform is asked the
same portable body (`portable_digest` is shared across a request's cells) while
`request_digest` differs. The artifact also stores the per-platform realization gaps,
which is how the VMware boundary (no address on the workload) stays visible rather
than being silently dropped. No cell claims native contact, placement authority or
production authorization.

`neutron_observation.json.example` and `accepted_route_record.json.example` contain
intentionally unusable placeholders. Populate actual expectations from accepted
engineering and inventory records, never by treating example values as approvals.
Every root's `inputs.tfvars.json.example` is disabled. Credentials must be injected
through the approved execution environment and are not part of these files.
