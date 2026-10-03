"""Pure/local inventory checks; never opens a native connection."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from datetime import datetime, timezone
from provisioner.execution.guest_inventory import gate, timestamp
from provisioner.execution.guest_services import resolver_bound


def guest_gate(enabled, outputs, access, known_hosts, targets, hostvars):
    # ansible-core 2.19 tags inventory scalars (including int subclasses).
    # Normalize JSON inputs at this boundary; the pure validator still rejects
    # booleans, strings, floats and unsupported objects where integers are required.
    outputs = json.loads(json.dumps(outputs, allow_nan=False))
    access = json.loads(json.dumps(access, allow_nan=False))
    return gate(enabled, outputs, access, known_hosts, targets, hostvars)


class FilterModule:
    def filters(self):
        return {'hosting_guest_gate': guest_gate,
                'hosting_resolvers_bound': resolver_bound,
                'hosting_handoff_current': lambda value: timestamp(value) > datetime.now(timezone.utc)}
