# Examples and synthetic fixtures

`wd14-routing.json` is the unchanged documentation topology. The offline route
auditor covers both address families; the actual namespace fixture executes only
its IPv4 subset. None of its prefixes are site allocations.

The saved plans named `synthetic_*` are constructed unit-test fixtures, not outputs
from Terraform. Native provider plans cannot be claimed while the engine is absent.

`neutron_observation.json.example` and `accepted_route_record.json.example` contain
intentionally unusable placeholders. Populate actual expectations from accepted
engineering and inventory records, never by treating example values as approvals.
Every root's `inputs.tfvars.json.example` is disabled. Credentials must be injected
through the approved execution environment and are not part of these files.
