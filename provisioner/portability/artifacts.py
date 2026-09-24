"""Reviewed logical workload artifact registry.

A portable workload names an artifact by logical identity and content digest. Native
image/template identifiers are realization data and are resolved here, never accepted
from the consumer mobility request.
"""
from __future__ import annotations

import json
from pathlib import Path

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest
from provisioner.repository import ROOT

REGISTRY = ROOT / 'sources' / 'artifacts' / 'portable_workload_artifacts.json'
FORMAT = 'hosting-portable-workload-artifacts/1'


def load(path: Path | str | None = None) -> dict:
    target = Path(path) if path is not None else REGISTRY
    document = json.loads(target.read_text(encoding='utf-8'))
    if document.get('format') != FORMAT:
        raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                                f'Unknown portable artifact registry format '
                                f'{document.get("format")!r}',
                                path=str(target))
    if not isinstance(document.get('artifacts'), dict):
        raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                                'Portable artifact registry must declare artifacts',
                                path=str(target))
    return document


def resolve(image: dict, platform: str, site: str, path: Path | str | None = None) -> dict:
    """Resolve one logical artifact into reviewed native inputs for one selected site."""
    document = load(path)
    artifact_ref = image['artifactRef']
    row = document['artifacts'].get(artifact_ref)
    if row is None:
        raise ProvisioningError(
            'INVENTORY_INCOMPLETE',
            f'No reviewed artifact realization exists for {artifact_ref!r}',
            path='$.spec.artifact.image.artifactRef',
            details={'artifact_ref': artifact_ref, 'platform': platform})
    expected = {
        'sha256': image['sha256'],
        'architecture': image['architecture'],
        'firmware': image['firmware'],
    }
    actual = {key: row.get(key) for key in expected}
    if actual != expected or image['format'] not in row.get('formats', []):
        raise ProvisioningError(
            'ARTIFACT_INTEGRITY_FAILED',
            'Mobility artifact metadata differs from the reviewed artifact registry',
            path='$.spec.artifact.image',
            details={'artifact_ref': artifact_ref, 'expected': expected,
                     'registry': actual, 'format': image['format'],
                     'formats': list(row.get('formats', []))})
    platform_sites = row.get('platforms', {}).get(platform)
    site_entry = platform_sites.get(site) if isinstance(platform_sites, dict) else None
    native = site_entry.get('native_inputs') if isinstance(site_entry, dict) else None
    if not isinstance(native, dict) or not native:
        raise ProvisioningError(
            'REALIZATION_INPUT_UNAVAILABLE',
            f'Artifact {artifact_ref!r} has no reviewed realization for '
            f'{platform}/{site}',
            path='$.spec.target.platform',
            details={'artifact_ref': artifact_ref, 'platform': platform, 'site': site})
    reference = {
        'format': document['format'],
        'status': document.get('status', ''),
        'source': document.get('source', ''),
        'registry_digest': digest(document),
        'artifact_ref': artifact_ref,
        'artifact_sha256': row['sha256'],
        'platform': platform,
        'site': site,
    }
    return {'reference': reference, 'native_inputs': dict(native)}
