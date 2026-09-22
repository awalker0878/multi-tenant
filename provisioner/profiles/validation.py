"""Validation of a resolved profile set against the reviewed catalogs."""
from __future__ import annotations

from provisioner.domain.errors import Diagnostics
from provisioner.profiles.loader import Catalog
from provisioner.profiles.resolver import Resolution

IMPLEMENTED_ZONES = ('OZ', 'RZ')
IMPLEMENTED_FAMILIES = ('ipv4',)


def validate(resolution: Resolution, catalogs: Catalog, capability_ids) -> Diagnostics:
    diagnostics = Diagnostics()
    environment = catalogs.get('environment', resolution.profiles['environment'])
    requirements = environment.requires

    for family, key in (('security', 'security_min_rank'), ('assurance', 'assurance_min_rank'),
                        ('availability', 'availability_min_rank')):
        name = resolution.profiles[family]
        if name is None:
            diagnostics.add('SEMANTIC_INCONSISTENT',
                            f'Environment profile {environment.profile} requires a {family} profile',
                            path=f'$.spec.{family}.profile')
            continue
        profile = catalogs.get(family, name)
        if profile.rank < requirements.get(key, 0):
            diagnostics.add('POLICY_VIOLATION',
                            f'{family} profile {profile.profile} is below the minimum for '
                            f'environment profile {environment.profile}',
                            path=f'$.spec.{family}.profile',
                            details={'minimum_rank': requirements.get(key), 'actual_rank': profile.rank})

    if requirements.get('recovery') and resolution.profiles.get('recovery') is None:
        diagnostics.add('POLICY_VIOLATION',
                        f'Environment profile {environment.profile} requires recovery to be enabled',
                        path='$.spec.recovery.enabled')
    if resolution.profiles.get('recovery') is not None:
        assurance = catalogs.get('assurance', resolution.profiles['assurance'])
        recovery = catalogs.get('recovery', resolution.profiles['recovery'])
        for required_service in recovery.requires.get('services', []):
            if required_service not in resolution.services:
                diagnostics.add('SEMANTIC_INCONSISTENT',
                                f'Recovery profile {recovery.profile} requires the {required_service} service',
                                path='$.spec.services')

    unknown_zones = [z for z in resolution.zones if z not in IMPLEMENTED_ZONES]
    if unknown_zones:
        diagnostics.add('UNSUPPORTED_FEATURE',
                        f'Zones {unknown_zones} have no implemented internal composition',
                        path='$.spec.availability.profile',
                        details={'implemented_zones': list(IMPLEMENTED_ZONES)})

    family = resolution.network['address_family']
    if family not in IMPLEMENTED_FAMILIES:
        diagnostics.add('UNSUPPORTED_FEATURE',
                        f'Address family {family} has no implemented internal composition',
                        path='$.spec.network.profile',
                        details={'implemented_families': list(IMPLEMENTED_FAMILIES)})

    unknown = sorted(set(resolution.required_capabilities) - set(capability_ids))
    if unknown:
        diagnostics.add('UNSUPPORTED_PROFILE',
                        f'Resolved profiles require unknown capabilities: {unknown}',
                        path='$.spec',
                        details={'capability_ids': sorted(capability_ids)})

    if not resolution.required_capabilities:
        diagnostics.add('SEMANTIC_INCONSISTENT', 'Resolved profile set requires no capability',
                        path='$.spec')
    return diagnostics