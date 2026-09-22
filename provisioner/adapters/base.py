"""The platform adapter boundary.

An adapter declares *only* the native field shapes and module identities a
platform realization needs. It never provisions, never contacts a platform and
never decides placement. The native field sets are re-exported from the existing
compiler so the adapter and the compiler cannot drift apart.
"""
from __future__ import annotations

from dataclasses import dataclass

from provisioner.placement import eligibility
from provisioner.repository import repository_module

ADAPTER_FORMAT = 'hosting-platform-adapter/1'

_NOT_QUALIFIED = 'NATIVE_QUALIFICATION_ABSENT'


def _compiler():
    return repository_module('tools.compile_wsd')


def _components():
    return repository_module('scripts.build_wsd_compositions').COMPONENTS


@dataclass(frozen=True)
class Adapter:
    """One platform realization boundary."""

    platform: str
    family: str
    domains_module: str
    workloads_module: str
    placement_fields: frozenset
    network_fields: frozenset
    security_edge: str
    limits: tuple[str, ...] = ()
    format: str = ADAPTER_FORMAT

    @property
    def product_tuple(self) -> str:
        return eligibility.product_tuple(self.platform)

    @property
    def qualified(self) -> bool:
        return self.product_tuple != 'UNSELECTED'

    def placement_shape(self) -> dict:
        return {'required': sorted(self.placement_fields),
                'supplied_by': 'inventory cluster native identity'}

    def network_shape(self) -> dict:
        return {'required': sorted(self.network_fields),
                'supplied_by': 'native readback after the domain phase'}

    def to_dict(self) -> dict:
        return {'format': self.format, 'platform': self.platform, 'family': self.family,
                'product_tuple': self.product_tuple,
                'qualified': self.qualified,
                'status': _NOT_QUALIFIED if not self.qualified else 'QUALIFIED',
                'modules': {'domains': self.domains_module, 'workloads': self.workloads_module},
                'placement_shape': self.placement_shape(),
                'network_shape': self.network_shape(),
                'security_edge': self.security_edge,
                'limits': list(self.limits),
                'native_contact': False}


def _adapter(platform: str, security_edge: str, limits: tuple[str, ...]) -> Adapter:
    modules = _components()[platform]
    compiler = _compiler()
    return Adapter(platform=platform, family=eligibility.PLATFORM_FAMILY[platform],
                   domains_module=modules['domains'], workloads_module=modules['workloads'],
                   placement_fields=frozenset(compiler.PLACEMENT[platform]),
                   network_fields=frozenset(compiler.NETWORK[platform]),
                   security_edge=security_edge, limits=limits)


def adapters() -> dict[str, Adapter]:
    """Every adapter this repository currently declares."""
    from provisioner.adapters import nutanix, openstack, vmware
    return {a.platform: a for a in (nutanix.adapter(), vmware.adapter(),
                                    openstack.adapter())}


def get(platform: str) -> Adapter:
    try:
        return adapters()[platform]
    except KeyError as exc:
        raise ValueError(f'No adapter declares platform {platform!r}') from exc