"""Semantic (cross-field) validation of a normalized request."""
from __future__ import annotations

from provisioner.domain.errors import Diagnostics
from provisioner.profiles.loader import Catalog
from provisioner.profiles.resolver import Resolution


def validate(document: dict, resolution: Resolution, catalogs: Catalog) -> Diagnostics:
    """Refuse requests that are schema-valid but semantically impossible."""
    diagnostics = Diagnostics()
    spec = document['spec']
    metadata = document['metadata']

    if metadata['tenant'] == metadata['name']:
        diagnostics.add('SEMANTIC_INCONSISTENT',
                        'Tenant and workload security domain identity must differ',
                        path='$.metadata.name')

    zones = spec.get('zones', {})
    if not zones.get('operations', {}).get('enabled', True):
        diagnostics.add('SEMANTIC_INCONSISTENT',
                        'The operations zone cannot be disabled; every internal domain needs one',
                        path='$.spec.zones.operations.enabled')
    if not zones.get('restricted', {}).get('enabled', True) and 'RZ' in resolution.zones:
        diagnostics.add('SEMANTIC_INCONSISTENT',
                        'The restricted zone is required by the selected availability profile',
                        path='$.spec.zones.restricted.enabled',
                        details={'zones': list(resolution.zones)})

    exposure = spec.get('exposure', {})
    if exposure.get('publicIngress'):
        diagnostics.add('UNSUPPORTED_FEATURE',
                        'No public ingress path is implemented; internal OZ/RZ only',
                        path='$.spec.exposure.publicIngress')
    if exposure.get('internetEgress'):
        diagnostics.add('UNSUPPORTED_FEATURE',
                        'No internet egress path is implemented; internal OZ/RZ only',
                        path='$.spec.exposure.internetEgress')

    security = catalogs.get('security', resolution.profiles['security'])
    if security.service_class == 'protected-b' and resolution.services.get('logging') != 'logging/protected-b':
        diagnostics.add('SEMANTIC_INCONSISTENT',
                        'A protected service class requires the protected log collection profile',
                        path='$.spec.services.logging',
                        details={'required': 'protected-b', 'actual': resolution.services.get('logging')})

    placement = spec['placement']
    if spec['platform']['preference'] == 'auto' and placement.get('cell'):
        diagnostics.add('SEMANTIC_INCONSISTENT',
                        'A pinned cell requires an explicit platform preference',
                        path='$.spec.placement.cell')
    if placement.get('cell') and placement.get('site') is None:
        diagnostics.add('SEMANTIC_INCONSISTENT',
                        'A pinned cell must also name its site',
                        path='$.spec.placement.site')
    return diagnostics
