"""Typed catalog requirement fields; capability semantics have their own owner.

Reject ambiguous policy before resolution: strings are not booleans, booleans
are not quantities, and absent required fields cannot acquire code defaults.
These are representation bounds, not native platform maxima or qualification.
"""
from __future__ import annotations

from provisioner.domain.errors import ProvisioningError

_MAX = 2**63 - 1
_GIB_MAX = _MAX // 1024**3
# (type, minimum, maximum); each family owns the fields its runtime consumes.
_FIELDS = {
    'assurance': {'recovery_required': bool},
    'availability': {'zones': list, 'min_workloads_per_zone': (int, 1, _MAX)},
    'compute': {'vcpu': (int, 1, _MAX), 'memory_gib': (int, 1, _GIB_MAX),
                'boot_disk_gib': (int, 1, _GIB_MAX),
                'workloads_per_zone': (int, 1, _MAX), 'flavor_class': str},
    'environment': {'lifecycle': str, 'security_min_rank': (int, 1, _MAX),
                    'assurance_min_rank': (int, 1, _MAX),
                    'availability_min_rank': (int, 1, _MAX), 'recovery': bool},
    'network': {'address_family': str, 'prefix_length': (int, 0, 128),
                'gateway_host_number': (int, 0, _MAX)},
    'placement': {'selection': str},
    'recovery': {'services': list, 'recovery_zone': str, 'independent_site': bool},
    'security': {'trust': str, 'service_class': str, 'zones': list,
                 'public_ingress': bool, 'internet_egress': bool},
    'service': {'service': str, 'binding_class': str},
    'storage': {'data_disk_gib': (int, 0, _GIB_MAX), 'storage_class': str},
}
_OPTIONAL = {'recovery': frozenset({'independent_site'})}


def _text(value: object) -> bool:
    return (type(value) is str and 1 <= len(value) <= 128
            and value == value.strip() and all(32 <= ord(char) <= 126 for char in value))


def validate_requirements(family: str, values: dict, *, path: str) -> None:
    """One closed field/type owner; constraints are parsed by capability_properties."""
    def refuse(message: str, key: str | None = None) -> None:
        raise ProvisioningError('UNSUPPORTED_PROFILE', message,
                                path=f'{path}.requires' + (f'.{key}' if key else ''))

    if family not in _FIELDS:
        refuse(f'Unknown profile family: {family}')
    fields = _FIELDS[family]
    if type(values) is not dict:
        refuse('Profile requirements must be a mapping')
    if set(values) - fields.keys() - {'capabilities', 'constraints'}:
        refuse('Unknown profile requirement field')
    missing = fields.keys() - values.keys() - _OPTIONAL.get(family, frozenset())
    if missing:
        refuse(f'Missing profile requirements: {sorted(missing)}')
    for key, expected in fields.items():
        if key not in values:
            continue
        value = values[key]
        if isinstance(expected, tuple):
            if type(value) is not int or not expected[1] <= value <= expected[2]:
                refuse('Profile quantity must be an integer within its representation bounds', key)
        elif expected is str:
            if not _text(value):
                refuse('Profile requirement must be bounded nonempty text', key)
        elif expected is bool:
            if type(value) is not bool:
                refuse('Profile policy flag must be a boolean', key)
        elif expected is list:
            if (type(value) is not list or not 1 <= len(value) <= 64
                    or not all(_text(item) for item in value)
                    or len(value) != len(set(value))):
                refuse('Profile relationship set must be bounded, nonempty and unique', key)

    if family == 'network':
        address_family = values['address_family']
        if address_family not in ('ipv4', 'ipv6', 'dual'):
            refuse('Unknown address family', 'address_family')
        bits = 128 if address_family == 'ipv6' else 32
        prefix, gateway = values['prefix_length'], values['gateway_host_number']
        if prefix > bits or gateway >= 2**(bits - prefix):
            refuse('Gateway offset or prefix exceeds the selected address family')
    if family == 'placement' and values['selection'] != 'lowest-cell-key':
        refuse('Placement selection has no implemented resolver', 'selection')
