"""One-shot installed collector: stage signed observations or publish original bytes.

Only a protected local configuration file selects dependencies. This command does
not admit campaigns, mint credentials, create database roles or perform migrations.
Publication is always explicit and cannot fall back to collection or re-signing.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.persistence.store import TenantContext

from .adapters.collector_config import create_native_collector
from .collector_settings import DiscoveryCollectorSettings, MAX_CONFIG_BYTES
from .ingest import _campaign, _signature
from .model import _id, _utc
from .native_credentials import decode_json, read_protected
from .publication import DiscoveryPublicationHeld, PrivateDiscoveryOutbox, PrivateFileDiscoveryResultSigner, stage_submission
from .publication_https import DiscoveryHttpsPublisher, DiscoveryPublicationUnknown
from .trust import SignedDiscoveryIngestVerifier, SignedFileDiscoveryTrustStore, _keys
from .witness import SignedFileDiscoveryCredentialAuthority


FORMAT = 'hosting-discovery-collector-outcome/1'


def execute(config_path, action: str, *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
    """Perform one requested action; return only bounded non-secret outcome metadata."""
    if action not in ('stage', 'publish') or not callable(clock):
        raise ValueError('An explicit stage or publish action is required')
    settings = DiscoveryCollectorSettings.from_file(config_path)
    document = _keys(decode_json(read_protected(settings.campaign_file, MAX_CONFIG_BYTES), MAX_CONFIG_BYTES),
                     {'environmentId', 'campaign', 'campaignSignature'})
    campaign, signature = _campaign(document['campaign']), _signature(document['campaignSignature'])
    environment = document['environmentId']
    if not _id(environment):
        raise ValueError('An exact environment identity is required')
    previous = campaign.issued_at

    def now():
        nonlocal previous
        at = clock()
        if not _utc(at) or not previous <= at < campaign.expires_at:
            raise DiscoveryPublicationHeld('Collector campaign expired or clock regressed')
        previous = at
        return at

    verifier = SignedDiscoveryIngestVerifier(
        SignedFileDiscoveryTrustStore(settings.trust.policy_file,
            authority_public_key=Ed25519PublicKey.from_public_bytes(settings.trust.root_key),
            minimum_revision=settings.trust.minimum_revision),
        SignedFileDiscoveryCredentialAuthority(settings.witness.policy_file,
            authority_public_key=Ed25519PublicKey.from_public_bytes(settings.witness.root_key),
            minimum_revision=settings.witness.minimum_revision))
    verifier.bind(signature).verify_campaign(campaign, environment, now())
    outbox = PrivateDiscoveryOutbox(settings.outbox_root,
        TenantContext(campaign.scope.organization_id, campaign.scope.tenant_id))
    original = outbox.for_campaign(campaign, environment)
    if original is not None:
        if original.campaign_signature != signature:
            raise DiscoveryPublicationHeld('Original campaign signature cannot be replaced')
        original.verify(verifier, now())
    collected = False
    if action == 'stage':
        if original is None:
            if settings.native_json is None or settings.signer_file is None:
                raise DiscoveryPublicationHeld('New collection requires native and signer configuration')

            def collect():
                nonlocal collected
                native = create_native_collector(settings.native_json, campaign, environment,
                                                  verifier.bind(signature), now)
                collected = True
                return native.collect()

            original = stage_submission(campaign, environment, signature, collect=collect,
                signer=PrivateFileDiscoveryResultSigner(settings.signer_file, key_id=settings.signer_key_id),
                verifier=verifier, outbox=outbox, clock=now)
        original.verify(verifier, now())
        return {'format': FORMAT, 'status': 'STAGED', 'campaignId': campaign.campaign_id,
                'environmentId': environment, 'requestDigest': original.digest,
                'resultDigest': original.result.digest, 'completeness': original.result.completeness,
                'objectCount': len(original.result.objects), 'collectionRequested': collected,
                'publicationAttempted': False, 'executionAuthorized': False}
    if original is None or settings.publish_target is None:
        raise DiscoveryPublicationHeld('Publication requires an existing original and pinned ingest target')
    receipt = DiscoveryHttpsPublisher(settings.publish_target, verifier=verifier,
        outbox=outbox, timeout=settings.publish_timeout, clock=now).publish(original)
    return {'format': FORMAT, 'status': 'PUBLISHED', 'campaignId': receipt.campaign_id,
            'environmentId': receipt.environment_id, 'requestDigest': receipt.request_digest,
            'resultDigest': receipt.result_digest, 'generation': receipt.generation,
            'completeness': receipt.completeness, 'collectionRequested': False,
            'publicationAttempted': True, 'executionAuthorized': False}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # Never echo unknown arguments that may contain a mistaken inline secret.
        raise ValueError('Invalid collector command arguments')


def main(argv=None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument('action', choices=('stage', 'publish'))
    parser.add_argument('--config', required=True, help='Absolute protected collector JSON file')
    try:
        args = parser.parse_args(argv)
        result = execute(args.config, args.action)
        code = 0
    except DiscoveryPublicationUnknown as exc:
        result = {'format': FORMAT, 'status': 'DELIVERY_UNKNOWN', 'requestDigest': exc.request_digest,
                  'phase': exc.phase, 'reconciliationRequired': True, 'executionAuthorized': False}
        code = 3
    except KeyboardInterrupt:
        result = {'format': FORMAT, 'status': 'INTERRUPTED',
                  'reconciliationRequired': True, 'executionAuthorized': False}
        code = 130
    except Exception:
        result = {'format': FORMAT, 'status': 'HELD', 'executionAuthorized': False}
        code = 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
