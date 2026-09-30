"""Closed native composition table for the installed discovery collector command.

Each factory wires the existing platform owner. No dotted import, custom command,
URL callback, permissive fallback or alternative inventory representation exists.
"""
from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ..collector_settings import MAX_CONFIG_BYTES, protected_path
from ..native_credentials import decode_json
from ..trust import _decode, _keys


def _ahv(row, campaign, environment, verifier, clock, key, read_gate):
    from .ahv_https import AhvHttpsTransport
    from .ahv_credentials import SignedFileAhvCredentialSource
    _keys(row['selection'], set())
    ca = _keys(row['caBundles'], {'native'})
    return AhvHttpsTransport(campaign, environment, verifier=verifier,
        credentials=SignedFileAhvCredentialSource(protected_path(row['credentialFile']),
            authority_public_key=key, minimum_revision=row['minimumRevision']),
        ca_bundle=protected_path(ca['native']), timeout=row['timeoutSeconds'],
        max_response_bytes=row['maxResponseBytes'], clock=clock, read_gate=read_gate)


def _vmware(row, campaign, environment, verifier, clock, key, read_gate):
    from .vmware_https import VmwareHttpsTransport
    from .vmware_credentials import SignedFileVmwareCredentialSource
    from .vmware_rest import FolderSelection
    selection = _keys(row['selection'], {'folderIds', 'coverageDigest'})
    ca = _keys(row['caBundles'], {'native'})
    folders = selection['folderIds']
    if not isinstance(folders, list) or not 1 <= len(folders) <= 128:
        raise ValueError('An exact bounded folder selection is required')
    return VmwareHttpsTransport(campaign,
        FolderSelection(campaign.scope, tuple(folders), selection['coverageDigest']),
        environment, verifier=verifier,
        credentials=SignedFileVmwareCredentialSource(protected_path(row['credentialFile']),
            authority_public_key=key, minimum_revision=row['minimumRevision']),
        ca_bundle=protected_path(ca['native']), timeout=row['timeoutSeconds'],
        max_response_bytes=row['maxResponseBytes'], clock=clock, read_gate=read_gate)


def _openstack(row, campaign, environment, verifier, clock, key, read_gate):
    from .openstack import OpenStackServiceEndpoints
    from .openstack_credentials import SignedFileOpenStackCredentialSource
    from .openstack_https import OpenStackHttpsTransport
    selection = _keys(row['selection'], {'compute', 'volume', 'network'})
    ca = _keys(row['caBundles'], {'compute', 'volume', 'network'})
    return OpenStackHttpsTransport(campaign, OpenStackServiceEndpoints(
        campaign.scope.endpoint_id, campaign.scope.native_scope_id, **selection),
        environment, verifier=verifier,
        credentials=SignedFileOpenStackCredentialSource(protected_path(row['credentialFile']),
            authority_public_key=key, minimum_revision=row['minimumRevision']),
        ca_bundles={name: protected_path(value) for name, value in ca.items()},
        timeout=row['timeoutSeconds'], max_response_bytes=row['maxResponseBytes'], clock=clock, read_gate=read_gate)


# Exact existing collector IDs are admission selectors, not new capability claims.
_FACTORIES = {
    'nutanix-ahv-v4.0-hardware-2': _ahv,
    'vcenter-rest-vm-info-8.0.3.0-visible-only-2': _vmware,
    'openstack-project-https-1': _openstack,
}


def create_native_collector(native_json, campaign, environment, verifier, clock, *, read_gate=None):
    row = decode_json(native_json.encode('ascii'), MAX_CONFIG_BYTES)
    if row['profile'] != campaign.collector_id or row['profile'] not in _FACTORIES:
        raise ValueError('The native profile is not the exact admitted collector')
    key = Ed25519PublicKey.from_public_bytes(_decode(row['authorityKey'], 32))
    return _FACTORIES[row['profile']](row, campaign, environment, verifier, clock, key, read_gate)
