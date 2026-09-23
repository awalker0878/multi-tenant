"""Delivery plan assembly.

A delivery plan enumerates every operation this decision needs and names the owner
that must perform it. It exists so a reviewer can see the external boundaries
before anything is executed. No operation is ever performed here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest
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
    generation: int = 1
    operation_id: str = ''

    def to_dict(self) -> dict:
        return {'name': self.name, 'owner': self.owner, 'description': self.description,
                'status': self.status, 'blocking': self.blocking,
                'generation': self.generation, 'operation_id': self.operation_id,
                'details': dict(self.details)}


def _operation(name: str, details: dict | None = None, generation: int = 1,
               operation_id: str = '') -> Operation:
    owner, description, status = OPERATIONS[name]
    return Operation(name=name, owner=owner, description=description, status=status,
                     blocking=status == BLOCKING, details=dict(details or {}),
                     generation=generation, operation_id=operation_id)


def build(state, scopes: list[dict], plan_digest: str = '',
          operation_id: str = '') -> dict:
    """Enumerate the operations this decision requires, with their owners.

    Every operation is bound to the generation it belongs to and to the operation
    identity of that generation, so a receipt produced for one generation can never
    be read as a receipt for another. The binding is derived, never chosen: the same
    reviewed plan always names the same operations.
    """
    if not state.domains:
        raise ProvisioningError('COMPILATION_FAILED',
                                'A delivery plan requires at least one resolved domain',
                                path='desired_state.domains')
    identity = state.identity
    addresses = sorted(w.address for d in state.domains for w in d.workloads)
    operations = [
        _operation('state-backend', {'state_keys': sorted(s['state_key'] for s in scopes)},
                   state.generation, _operation_id(operation_id, 'state-backend')),
        _operation('capacity-reservation',
                   {'reservations': {z: r for z, r in sorted(state.reservations.items())}},
                   state.generation, _operation_id(operation_id, 'capacity-reservation')),
        _operation('address-allocation',
                   {'prefixes': sorted(d.prefix for d in state.domains),
                    'addresses': addresses},
                   state.generation, _operation_id(operation_id, 'address-allocation')),
        _operation('dns-registration',
                   {'names': sorted(w.name for d in state.domains for w in d.workloads),
                    'zone': _zone(state)},
                   state.generation, _operation_id(operation_id, 'dns-registration')),
        _operation('security-edge-route',
                   {'cells': sorted({d.cell_key for d in state.domains})},
                   state.generation, _operation_id(operation_id, 'security-edge-route')),
        _operation('shared-service-handoff',
                   {'services': sorted(state.services)},
                   state.generation, _operation_id(operation_id, 'shared-service-handoff')),
        _operation('backup-retention', {'recovery': state.profiles.get('recovery')},
                   state.generation, _operation_id(operation_id, 'backup-retention')),
        _operation('native-qualification', {'product_tuple': state.placement.get('platform')},
                   state.generation, _operation_id(operation_id, 'native-qualification')),
        _operation('production-authorization', {'lifecycle': state.lifecycle},
                   state.generation, _operation_id(operation_id, 'production-authorization')),
        _operation('guest-configuration', {'workloads': len(addresses)},
                   state.generation, _operation_id(operation_id, 'guest-configuration')),
    ]
    return {'format': DELIVERY_FORMAT,
            'status': 'PLANNED_DISABLED_NOT_AUTHORIZED',
            'generation': state.generation,
            'identity': identity.to_dict(),
            'operation_id': operation_id,
            'plan_digest': plan_digest,
            'operations': [o.to_dict() for o in operations],
            'blocking': sorted(o.name for o in operations if o.blocking),
            'terraform': terraform.to_dict(state.platform),
            'native_contact': False,
            'limits': ['Every operation is performed by the named owner, not by this repository',
                       'A blocking operation prevents activation, not planning',
                       'A receipt is bound to one generation and never carries to another']}


def _operation_id(operation_id: str, name: str) -> str:
    """The generation-scoped identity of one owner operation.

    Shaped like the operation identity it extends — and therefore like the
    `hosting-delivery/1` identifier the existing runner enforces — so a receipt
    issued for one generation of one operation can never be read as a receipt for
    another.
    """
    return f'{operation_id}-{name}' if operation_id else ''


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


def graph_digest(state, scopes: list[dict]) -> str:
    """The identity of the delivery graph a reviewed plan requires.

    The graph is the operations this decision needs and the owner each is handed to.
    It is a pure function of the reviewed decision, so it can be bound into the plan
    manifest before the derived plan identity exists. The derived keys (`plan_digest`,
    `operation_id` and the per-operation operation identities) are deliberately
    excluded: they are computed from the manifest, so including them here would make
    the identity self-referential.
    """
    document = build(state, scopes)
    return digest({'status': document['status'],
                   'blocking': document['blocking'],
                   'terraform': document['terraform'],
                   'operations': [{k: operation[k] for k in
                                   ('name', 'owner', 'status', 'blocking', 'details')}
                                  for operation in document['operations']]})