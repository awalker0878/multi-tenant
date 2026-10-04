"""Installed authenticated retained-state intake/import/handover command.

This process verifies existing evidence; it has no checkpoint signing identity,
key-enrollment privilege, local custody fallback or native execution callback.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

from provisioner.controlplane.evidence.runtime import (
    EvidenceRuntimeConfig, _private_file, _required, build_gate)
from provisioner.controlplane.persistence import TenantContext
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import encoded, read_private, require, write_new
from .handover import RetainedStateHandover
from .importer import RetainedStateImporter, prepare_source
from .originals import RetainedOriginalStore
from .proofs import ConversionProofs, PURPOSES


def build_importer(values=None, *, intake=False) -> RetainedStateImporter:
    env = os.environ if values is None else values
    config = EvidenceRuntimeConfig.from_environment(env)
    gate = build_gate(config, allow_signing=False)
    bucket = _required(env, 'HOSTING_CONVERSION_ORIGINAL_BUCKET')
    require(bucket not in {config.artifact_bucket, config.checkpoint_bucket},
            'Raw originals require a separate restricted Object Lock bucket')
    originals = RetainedOriginalStore(gate.evidence._artifacts.client, bucket,
        retention_days=config.retention_days,
        prefix=_required(env, 'HOSTING_CONVERSION_ORIGINAL_PREFIX'),
        kms_key_id=_required(env, 'HOSTING_CONVERSION_ORIGINAL_KMS_KEY_ID'))
    connect = lambda: psycopg.connect(config.postgres_dsn, connect_timeout=5)
    verify_connect = connect
    if intake:
        # URI form fits the existing bounded, private credential-file owner.
        # Only this separately enrolled non-bypass role can certify a receipt.
        dsn = _private_file(Path(_required(env, 'HOSTING_CONVERSION_VERIFIER_DSN_FILE')))
        settings = conninfo_to_dict(dsn)
        require(settings.get('sslmode') == 'verify-full' and settings.get('host')
            and not settings['host'].startswith('/') and ',' not in settings['host'],
            'Independent proof verifier requires exact verify-full PostgreSQL TLS')
        verify_connect = lambda: psycopg.connect(dsn, connect_timeout=5)
    proofs = ConversionProofs(verify_connect, evidence_gate=gate,
                              verifier=gate.evidence._verifier)
    return RetainedStateImporter(connect, proofs=proofs, originals=originals,
                                evidence_gate=gate)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Authenticated retained-state conversion')
    parser.add_argument('mode', choices=('propose', 'intake', 'import', 'inspect', 'handover'))
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--proof-events', type=Path)
    parser.add_argument('--purpose', choices=sorted(PURPOSES))
    parser.add_argument('--event-key')
    parser.add_argument('--organization-id')
    parser.add_argument('--tenant-id')
    parser.add_argument('--batch-id')
    args = parser.parse_args(argv)
    try:
        importer = build_importer(intake=args.mode == 'intake')
        if args.mode in {'propose', 'import', 'intake'}:
            require(args.manifest is not None, 'Explicit retained import manifest required')
            if args.mode == 'intake':
                raw_manifest=read_private(args.manifest)
                value = strict_loads(raw_manifest)
                inventory = value['inventory']
                from provisioner.execution.run_files import digest
                require(args.purpose is not None and args.event_key is not None,
                        'One exact separately retained proof purpose/event required')
                scope = inventory['scope']
                importer.proofs.intake(TenantContext(scope['organizationId'], scope['tenantId']),
                    scope, event_key=args.event_key, batch_id=inventory['batchId'],
                    manifest_digest=digest(raw_manifest), purpose=args.purpose)
                result = {'format':'hosting-retained-proof-intake/1','purpose':args.purpose,
                          'retained':True,'writesAuthorized':False,'retryAuthorized':False}
            elif args.mode == 'propose':
                require(args.source_root is not None and args.output is not None,
                        'Source root and private proposal output required')
                with importer._connect() as connection:
                    now = connection.execute('SELECT clock_timestamp()').fetchone()[0]
                proposal = prepare_source(args.manifest, args.source_root, as_of=now).proposal()
                write_new(args.output, encoded(proposal))
                result = {'format':proposal['format'],'serviceMode':'OBSERVATION_ONLY',
                          'writesAuthorized':False,'retryAuthorized':False}
            else:
                require(args.source_root is not None and args.proof_events is not None,
                        'Source root and separately verified proof events required')
                receipt = importer.import_batch(args.manifest, args.source_root,
                    proof_events=strict_loads(read_private(args.proof_events)))
                result = {'format':'hosting-retained-import-receipt/1',**asdict(receipt)}
        else:
            require(args.organization_id and args.tenant_id and args.batch_id,
                    'Exact retained tenant and batch required')
            owner = RetainedStateHandover(importer)
            context = TenantContext(args.organization_id, args.tenant_id)
            if args.mode == 'inspect':
                require(args.output is not None, 'Private reconciliation output required')
                inspection = owner.inspect(context, args.batch_id)
                write_new(args.output, encoded(inspection))
                result = {'format':inspection['format'],'serviceMode':inspection['serviceMode'],
                          'retryAuthorized':False}
            else:
                require(args.proof_events is not None, 'Exact independent handover proof events required')
                receipt = owner.accept_handover(context, args.batch_id,
                    proof_events=strict_loads(read_private(args.proof_events)))
                result = {key:receipt[key] for key in ('format','batchId','handoverId','advanced','serviceMode','retryAuthorized')}
                result['nativeCount']=len(receipt['nativeEpochs'])
        print(json.dumps(result, sort_keys=True))
    except Exception:
        # Credentials, retained private files, endpoint addresses and native
        # inventory never enter a command error or standard output.
        raise SystemExit('Retained-state conversion is unavailable or held') from None
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
