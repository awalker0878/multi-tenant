"""E2-only signed fixture custody. Enrolled fixture keys never qualify native platforms."""

import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    separators=(',', ':')).encode()).hexdigest()


def signed_fixture(record, directory, now=None, inventory=None, snapshot=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    now = int(time.time()) if now is None else now
    source = Path(__file__).resolve().parents[2] / 'contracts/capabilities/definitions-v1.json'
    definition = digest(json.loads(source.read_text()))
    scope = record['scope']
    keys = {}
    for role in ('observer', 'reviewer'):
        private = directory / (role + '.pem')
        if not private.is_file():
            subprocess.run(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048',
                            '-out', str(private)], check=True, capture_output=True)
            private.chmod(0o600)
        public = subprocess.check_output(['openssl', 'pkey', '-in', str(private), '-pubout'], text=True)
        keys[role] = {'role': role, 'subject_id': 'fixture-' + role, 'public_key_pem': public,
                      'scope': {k: scope[k] for k in ('tenant_id', 'site_id', 'endpoint_id')},
                      'expires_at': now + 7200}

    def sign(payload, role):
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()
        signature = subprocess.check_output(['openssl', 'dgst', '-sha256', '-sign',
                                             str(directory / (role + '.pem'))], input=raw)
        return {'key_id': role, 'content_base64': base64.b64encode(raw).decode(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'signature_base64': base64.b64encode(signature).decode()}

    record = copy.deepcopy(record)
    record.pop('verification', None)
    record.update(version=2, evidence_level='E3')
    proof = {'kind': 'native_conformance', 'simulation': False, 'finalized': True,
             'scope_sha256': digest(scope), 'definition_sha256': definition,
             'runtime_artifacts': scope['artifacts'], 'adapter_conformant': True,
             'dimensions': record['dimensions'], 'capabilities': record['capabilities'],
             'cases': ({'capability:' + k: 'passed' for k in record['capabilities']}
                       | {'dimension:' + k: 'passed' for k in record['dimensions']}
                       | {'adapter_behavior':'passed','installed_identity':'passed','runtime_artifacts':'passed'}),
             'observed_at': now, 'expires_at': now + 3600, 'subject_id': keys['observer']['subject_id']}
    if inventory is not None:
        proof['inventory']=copy.deepcopy(inventory)
        proof['snapshot']=copy.deepcopy(snapshot)
    evidence = sign(proof, 'observer')
    record['evidence_refs'] = [evidence['sha256']]
    decision = sign({'kind': 'qualification_decision', 'decision': 'accepted_native',
                     'record_sha256': digest(record), 'definition_sha256': definition,
                     'evidence_sha256': record['evidence_refs'], 'revision': 1,
                     'scope_sha256': digest(scope), 'requested_by': 'fixture-requester',
                     'subject_id': keys['reviewer']['subject_id'], 'observed_at': now,
                     'expires_at': now + 3600}, 'reviewer')
    runtime = sign(proof | {'decision_sha256': decision['sha256'], 'expires_at': now + 120}, 'observer')
    return {'record': record, 'decision': decision, 'evidence': [evidence], 'runtime': runtime}, keys


def refresh_runtime(envelope, directory, now=None):
    now = int(time.time()) if now is None else now
    payload = json.loads(base64.b64decode(envelope['content_base64']))
    payload.update(observed_at=now, expires_at=now+120)
    # E2 peer measurements are deliberately simulated, never native commissioning evidence.
    snapshot=payload.get('snapshot',{})
    if snapshot:
        snapshot['isolation'].update(observed_at=now,expires_at=now+120)
        for row in snapshot['network']['measurements']+snapshot['recovery_measurements']:
            row.update(observed_at=now,expires_at=now+120)
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()
    signature=subprocess.check_output(['openssl','dgst','-sha256','-sign',str(Path(directory)/'observer.pem')],input=raw)
    return {'key_id':envelope['key_id'],'content_base64':base64.b64encode(raw).decode(),
            'sha256':hashlib.sha256(raw).hexdigest(),'signature_base64':base64.b64encode(signature).decode()}


class FixtureRuntimePublisher:
    """Refreshes synthetic peer evidence only; qualification review bytes remain immutable."""
    def __init__(self, path, registry, directory):
        import threading
        self.path, self.registry, self.directory = Path(path), registry, Path(directory)
        self.stop=threading.Event()
        self.refresh()
        self.thread=threading.Thread(target=self.run,daemon=True)
        self.thread.start()

    def refresh(self):
        records={row['decision']['sha256']:refresh_runtime(row['runtime'],self.directory/('fixture-keys-'+row['record']['scope']['site_id'])) for row in self.registry['records']}
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'schema_version':1,'records':records}))
        temporary.chmod(0o600)
        temporary.replace(self.path)

    def run(self):
        while not self.stop.wait(15):
            self.refresh()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
