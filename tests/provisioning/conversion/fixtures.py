"""Synthetic external ports; canonical and old writer contracts remain real."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.conversion.importer import FORMAT, prepare_source
from provisioner.controlplane.conversion.proofs import PROOF_FORMAT, PURPOSES, scope_digest
from provisioner.controlplane.evidence.repository import _canonical
from provisioner.execution.run_files import digest, encoded, load_private, write_new


class CryptoTransit:
    """Only the HTTPS service boundary is substituted, with separate real keys."""

    def __init__(self):
        self.keys = {purpose.lower(): Ed25519PrivateKey.generate()
                     for purpose in {*PURPOSES, 'CHECKPOINT'}}
        self.calls = []

    def post(self, mount, operation, key, payload):
        assert mount == 'transit'
        self.calls.append((operation, key))
        raw = base64.b64decode(payload['input'], validate=True)
        if operation == 'sign':
            return {'signature':'vault:v1:' + base64.b64encode(self.keys[key].sign(raw)).decode()}
        assert operation == 'verify'
        try:
            version, revision, signed = payload['signature'].split(':')
            if (version, revision) != ('vault', 'v1'):
                return {'valid':False}
            self.keys[key].public_key().verify(base64.b64decode(signed, validate=True), raw)
            return {'valid':True}
        except (InvalidSignature, ValueError):
            return {'valid':False}

    def trust(self):
        return {purpose.lower(): ('transit', purpose.lower()) for purpose in {*PURPOSES,'CHECKPOINT'}}


def envelope(transit, purpose, prepared, statement, *, now=None):
    now = now or datetime.now(timezone.utc)
    payload = {'format':PROOF_FORMAT,'purpose':purpose,
        'batchId':prepared.value['inventory']['batchId'],'manifestDigest':prepared.batch_digest,
        'scopeDigest':scope_digest(prepared.value['inventory']['scope']),
        'statementDigest':digest(encoded(statement)),'subjectId':purpose.lower()+'-reviewer',
        'observedAt':(now-timedelta(seconds=1)).isoformat(),
        'freshUntil':(now+timedelta(minutes=4)).isoformat()}
    signature = transit.post('transit','sign',purpose.lower(),
        {'input':base64.b64encode(_canonical(payload)).decode()})['signature'].encode()
    return {'payload':payload,'statement':deepcopy(statement),'keyId':purpose.lower(),
            'signature':base64.b64encode(signature).decode()}


def absent_boundary(kind):
    return {'format':'hosting-retained-'+kind+'-boundary/1','mode':'NOT_DEPLOYED','recordCount':0,
            'snapshotDigest':'0'*64,'auditSequence':0,'auditHeadHash':'0'*64,
            'evidenceSequence':0,'evidenceHeadHash':'0'*64}


def authenticated_source(test, *, unknown=False, history=True):
    # Composition avoids inheriting/discovering the existing 21 rehearsal cases.
    from tests.provisioning.conversion import test_rehearsal
    f = test_rehearsal.RehearsalTests('runTest')
    f.setUp()
    test.addCleanup(f.doCleanups)
    suffix = uuid4().hex[:16]
    identities = {row['nativeId']:str(uuid4()) for row in f.bindings}
    replacements = {'org-01':'retained-'+suffix,'openstack-01':'openstack-'+suffix,
                    'project-01':'project-'+suffix,**identities}
    def scoped(value):
        if isinstance(value, dict): return {key:scoped(item) for key,item in value.items()}
        if isinstance(value, list): return [scoped(item) for item in value]
        return replacements.get(value, value) if isinstance(value, str) else value
    f.scope_record = scoped(f.scope_record)
    f.bindings = scoped(f.bindings)
    f.workload = scoped(f.workload)
    f.manifest['scope'] = f.scope_record
    f.manifest['batchId'] = 'batch-'+suffix
    for name in ('workload.json','native.json','freeze.json','owners.json','operations/run-01/outputs.json'):
        path = f.source_root/name
        path.write_bytes(encoded(scoped(load_private(path))))
    # Rebind the true old format's digest closure through its original owners.
    f.explicit_stage('prepared')
    if unknown:
        next(f.native_ledger.glob('*.result.json')).unlink()
        start = load_private(next(f.native_ledger.glob('*.started.json')))
        (f.native_ledger/'head.json').write_bytes(encoded(start))
        (f.source_root/'operations/run-01/result.json').unlink()
    history_files=[]
    if history:
        history_files=['history/workload-1.json']
        (f.source_root/'history').mkdir(mode=0o700)
        write_new(f.source_root/history_files[0],encoded(f.workload))
        current=deepcopy(f.workload)
        current['metadata'].update(revision=2,ownerId='retained-current-owner')
        (f.source_root/'workload.json').write_bytes(encoded(current))
    f.seal()
    boundary=absent_boundary('postgres')
    if history:
        names=sorted([*history_files,'workload.json'])
        boundary.update(mode='CANONICAL_FILES',recordCount=len(names),
            snapshotDigest=digest(encoded({name:digest((f.source_root/name).read_bytes()) for name in names})))
    value={'format':FORMAT,'inventory':f.manifest,'workloadHistoryFiles':history_files,
           'sourceDatabaseBoundary':boundary,'sourceWorkflowBoundary':absent_boundary('workflow')}
    path=f.base/'authenticated-manifest.json'
    write_new(path,encoded(value))
    return f,path,value


def initial_statements(prepared):
    inventory=prepared.value['inventory']
    native=prepared.snapshot.json(inventory['evidence']['nativeInventory'])
    freeze=prepared.snapshot.json(inventory['evidence']['oldWriterFreeze'])
    proposal=prepared.proposal()
    return {'IMPORT':proposal['importStatement'],'CUSTODY':proposal['custodyStatement'],
        'NATIVE':{'complete':True,'bindings':native['bindings'],
            'tasks':[{'operationId':row['operationId'],'generation':row['generation'],
                'outcome':'UNKNOWN' if row['outcome']=='UNKNOWN' else 'EFFECT_PRESENT',
                'nativeQuiesced':False,'nativeTaskIds':[]} for row in prepared.recoveries],
            'retainedNativeDigest':inventory['sourceFileSha256'][inventory['evidence']['nativeInventory']],
            'reconciliationDigest':None},
        'EXCLUSION':{'oldWriters':freeze['oldWriters'],'allExcluded':True,'queuedRequestsExcluded':True,
            'nativeTasksQuiesced':False,
            'retainedFreezeDigest':inventory['sourceFileSha256'][inventory['evidence']['oldWriterFreeze']],
            'reconciliationDigest':None}}
