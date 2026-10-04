"""One-shot collector: inspect custody, stage observations or publish original bytes.

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
from .read_budget import NativeReadGate
from .native_credentials import decode_json, read_protected
from .publication import DiscoveryPublicationHeld, PrivateDiscoveryOutbox, PrivateFileDiscoveryResultSigner, stage_submission
from .publication_https import DiscoveryHttpsPublisher, DiscoveryPublicationUnknown
from .trust import SignedDiscoveryIngestVerifier, SignedFileDiscoveryTrustStore, _keys
from .witness import SignedFileDiscoveryCredentialAuthority


FORMAT = 'hosting-discovery-collector-outcome/1'


def execute(config_path, action: str, *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
            config_digest: str | None = None, campaign_digest: str | None = None,
            environment_id: str | None = None, read_gate: NativeReadGate | None = None) -> dict:
    """Perform one requested action; return only bounded non-secret outcome metadata."""
    if action not in ('stage', 'publish', 'inspect') or not callable(clock):
        raise ValueError('An explicit inspect, stage or publish action is required')
    settings = DiscoveryCollectorSettings.from_file(config_path, expected_digest=config_digest)
    document = _keys(decode_json(read_protected(settings.campaign_file, MAX_CONFIG_BYTES), MAX_CONFIG_BYTES),
                     {'environmentId', 'campaign', 'campaignSignature'})
    campaign, signature = _campaign(document['campaign']), _signature(document['campaignSignature'])
    environment = document['environmentId']
    if not _id(environment):
        raise ValueError('An exact environment identity is required')
    if campaign_digest is not None and campaign.digest() != campaign_digest:
        raise DiscoveryPublicationHeld('Campaign differs from its scheduled authorization')
    if environment_id is not None and environment != environment_id:
        raise DiscoveryPublicationHeld('Environment differs from its scheduled selection')
    if read_gate is not None:
        if not isinstance(read_gate, NativeReadGate):
            raise TypeError('An endpoint read gate is required')
        read_gate.require_scope(campaign.scope)
    previous = campaign.issued_at

    def now():
        nonlocal previous
        if read_gate is not None:
            read_gate.check()
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
    from .fleet_read_budget import FleetNativeReadGate
    if action=='stage' and isinstance(read_gate,FleetNativeReadGate):
        # Bind only after the existing independently signed current campaign was
        # verified. The fleet owner reduces admission; it cannot issue authority.
        read_gate=read_gate.bind_campaign(campaign,environment)
        read_gate.budget.settings.enrollment.require_store('outbox',settings.outbox_root)
    outbox = PrivateDiscoveryOutbox(settings.outbox_root,
        TenantContext(campaign.scope.organization_id, campaign.scope.tenant_id))
    if action == 'inspect':
        return outbox.inspect(campaign, environment, signature, verifier=verifier, clock=now)
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
                                                  verifier.bind(signature), now, read_gate=read_gate)
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
    parser.add_argument('action', choices=('stage', 'publish', 'batch-stage', 'inspect', 'batch-inspect',
                        'batch-reconcile', 'batch-run', 'batch-publish', 'batch-retry-publication'))
    parser.add_argument('--config', required=True, help='Absolute protected collector JSON file')
    parser.add_argument('--state-directory', help='Existing private directory for one checkpointed batch')
    parser.add_argument('--fleet-state-directory', help='Existing private shared POSIX endpoint budget directory')
    parser.add_argument('--fleet-config', help='Protected enrolled PostgreSQL multi-host budget configuration')
    try:
        args = parser.parse_args(argv)
        if args.fleet_config is not None and (args.fleet_state_directory is not None
                or args.action not in ('batch-stage','batch-run')):
            raise ValueError('Select one fleet owner for collection batches')
        if args.fleet_state_directory is not None and args.action not in ('batch-stage', 'batch-run'):
            raise ValueError('Shared endpoint budgets are only supported for collection batch actions')
        if args.state_directory is not None and args.action not in ('batch-stage', 'batch-inspect',
                'batch-reconcile', 'batch-run', 'batch-publish', 'batch-retry-publication'):
            raise ValueError('State directory is only supported for batch actions')
        if args.action in ('batch-stage', 'batch-run'):
            from .batch_runtime import run_batch
            result = run_batch(args.config, state_directory=args.state_directory,
                               wait_for_due=args.action == 'batch-run',
                               fleet_state_directory=args.fleet_state_directory,fleet_config=args.fleet_config)
            code = 0 if result['status'] == 'BATCH_EVALUATED' else 2
        elif args.action in ('batch-inspect', 'batch-reconcile'):
            if args.state_directory is None:
                raise ValueError('An enrolled private journal is required')
            from .batch_runtime import inspect_batch
            result = inspect_batch(args.config, args.state_directory, reconcile=args.action == 'batch-reconcile')
            code = 0 if result['status'] == 'JOURNAL_INSPECTED' else 2
        elif args.action in ('batch-publish', 'batch-retry-publication'):
            if args.state_directory is None:
                raise ValueError('An enrolled private journal is required')
            from .batch_runtime import publish_batch
            result = publish_batch(args.config, args.state_directory,
                                   retry_unknown=args.action == 'batch-retry-publication')
            code = (0 if result['status'] == 'PUBLICATION_ACKNOWLEDGED' else
                    3 if result['unknownDeliveryCount'] else 2)
        else:
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
