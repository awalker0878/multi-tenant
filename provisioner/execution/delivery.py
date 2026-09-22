"""Delivery plan assembly.

A delivery plan enumerates every operation this decision needs and names the owner
that must perform it. It exists so a reviewer can see the external boundaries
before anything is executed. No operation is ever performed here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.domain.errors import ProvisioningError
from provisioner.execution import terraform

DELIVERY_FORMAT = 'hosting-delivery-plan/1'
REPOSITORY_OWNER = 'hosting-platform'

BLOCKING = 'BLOCKING'
DECLARED = 'DECLARED'
STATUSES = (BLOCKING, DECLARED)

# Operation -> (owner, description, blocking until satisfied)
OPERATIONS = {
    'state-backend': ('platform-owner',
                      'Provision the reviewed Terraform backend and match it to the state key', BLOCKING),
    'capacity-reservation': ('capacity-owner',
                             'Confirm the reserved vCPU, memory and storage against site capacity', BLOCKING),
    'address-allocation': ('ipam-owner',
                           'Confirm the reserved prefixes and addresses in the authoritative IPAM', BLOCKING),
    'dns-registration': ('dns-owner',
                         'Register the workload names in the authoritative zone', BLOCKING),
    'security-edge-route': ('security-edge-owner',
                            'Create the isolated upstream route and its policy', BLOCKING),
    'shared-service-handoff': ('service-owner',
                               'Accept the WSD as a consumer of the shared service profiles', DECLARED),
    'backup-retention': ('backup-owner',
                         'Apply the retention and restore policy for the resolved recovery profile', DECLARED),
    'native-qualification': ('platform-owner',
                             'Qualify the selected product tuple natively', BLOCKING),
    'production-authorization': ('service-owner',
                                 'Record separate production authorization', BLOCKING),
    'guest-configuration': ('platform-owner',
                            'Run the reviewed guest configuration after native identity exists', DECLARED),
}


@dataclass(frozen=True)
class Operation:
    name: str
    owner: str
    description: str
    status: str
    blocking: bool
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {'name': self.name, 'owner': self.owner, 'description': self.description,
                'status': self.status, 'blocking': self.blocking,
                'details': dict(self.details)}


def _operation(name: str, details: dict | None = None) -> Operation:
    owner, description, status = OPERATIONS[name]
    return Operation(name=name, owner=owner, description=description, status=status,
                     blocking=status == BLOCKING, details=dict(details or {}))


def build(state, scopes: list[dict]) -> dict:
    """Enumerate the operations this decision requires, with their owners."""
    if not state.domains:
        raise ProvisioningError('COMPILATION_FAILED',
                                'A delivery plan requires at least one resolved domain',
                                path='desired_state.domains')
    addresses = sorted(w.address for d in state.domains for w in d.workloads)
    operations = [
        _operation('state-backend', {'state_keys': sorted(s['state_key'] for s in scopes)}),
        _operation('capacity-reservation',
                   {'reservations': {z: r for z, r in sorted(state.reservations.items())}}),
        _operation('address-allocation',
                   {'prefixes': sorted(d.prefix for d in state.domains),
                    'addresses': addresses}),
        _operation('dns-registration',
                   {'names': sorted(w.name for d in state.domains for w in d.workloads),
                    'zone': _zone(state)}),
        _operation('security-edge-route',
                   {'cells': sorted({d.cell_key for d in state.domains})}),
        _operation('shared-service-handoff',
                   {'services': sorted(state.services)}),
        _operation('backup-retention', {'recovery': state.profiles.get('recovery')}),
        _operation('native-qualification', {'product_tuple': state.placement.get('platform')}),
        _operation('production-authorization', {'lifecycle': state.lifecycle}),
        _operation('guest-configuration', {'workloads': len(addresses)}),
    ]
    return {'format': DELIVERY_FORMAT,
            'status': 'PLANNED_DISABLED_NOT_AUTHORIZED',
            'operations': [o.to_dict() for o in operations],
            'blocking': sorted(o.name for o in operations if o.blocking),
            'terraform': terraform.to_dict(state.platform),
            'native_contact': False,
            'limits': ['Every operation is performed by the named owner, not by this repository',
                       'A blocking operation prevents activation, not planning']}


def _zone(state) -> str:
    for binding in state.service_bindings:
        if binding['service'] == 'dns':
            return binding['endpoints'].get('zone', '')
    return ''


def require_unblocked(delivery: dict) -> None:
    """Refuse activation while a blocking owner operation is outstanding."""
    if delivery['blocking']:
        raise ProvisioningError('EXECUTION_REFUSED',
                                'Blocking owner operations are outstanding',
                                path='$.delivery',
                                details={'blocking': delivery['blocking']})