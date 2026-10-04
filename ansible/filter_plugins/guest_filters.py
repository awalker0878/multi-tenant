"""Pure/local inventory checks; never opens a native connection."""
import sys
import json
import os
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
    session_path = os.environ.get('HOSTING_GUEST_COMMAND_SESSION')
    connection = 'ssh'
    if session_path is not None:
        from provisioner.execution.guest_command_client import authorize, load_session
        session = load_session(session_path)
        if list(access.get('targets', {}).values()) != [session['target']]:
            raise ValueError('The controller inventory differs from its original guest command session')
        authorize(session, command=['controller-gate', known_hosts])
        connection = 'hosting_guarded_ssh'
    return gate(enabled, outputs, access, known_hosts, targets, hostvars,
                expected_connection=connection)


class FilterModule:
    def filters(self):
        return {'hosting_guest_gate': guest_gate,
                'hosting_resolvers_bound': resolver_bound,
                'hosting_handoff_current': lambda value: timestamp(value) > datetime.now(timezone.utc)}
