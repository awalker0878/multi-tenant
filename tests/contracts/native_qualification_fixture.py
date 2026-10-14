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


def composition_readiness(content, tenant, now):
    """Current synthetic E2 resolver specimen; never enrolled E3/E4 evidence."""
    from importlib.util import module_from_spec, spec_from_file_location
    from lifecycle.domain.capability_definitions import METHOD_ALIASES
    root = Path(__file__).resolve().parents[2]
    locator = spec_from_file_location('_composition_readiness', root/'services/lifecycle/tests/test_migration_readiness.py')
    if locator is None or locator.loader is None:
        raise RuntimeError('Current Lifecycle readiness test specimen unavailable')
    fixture = module_from_spec(locator)
    locator.loader.exec_module(fixture)
    value, _ = fixture.specimen()
    migration = content['native_migration']['migration']
    value.update(scope={'tenant_id': tenant, 'application_id': content['scope']['resource_id'],
                        'environment_id': content['scope']['environment'], 'site_id': content['scope']['site_id']},
                 route_sha256=content['migration_campaign']['route_sha256'],
                 method=METHOD_ALIASES[migration['method']], evaluated_at=now, expires_at=now+100)
    for case in value['api_compatibility']['cases']:
        case['expires_at'] = now+100
    for side in ('source', 'target'):
        value[side].update(profile_sha256=migration[side]['profile_sha256'])
        if 'outcomes' in migration:
            value[side]['platform'] = migration['outcomes'][side+'_platform']
    recon = value['workload_reconciliation']
    recon.update(source_profile_sha256=migration['source']['profile_sha256'],
                 native_review_sha256=migration['review']['digest'], expires_at=now+100)
    recon['reconciliation_sha256'] = digest({k:v for k,v in recon.items() if k != 'reconciliation_sha256'})
    for coverage in value['collection_coverages']:
        side = 'target' if coverage['scope'] == 'target' else 'source'
        coverage.update(platform=value[side]['platform'], installed_tuple_sha256=migration[side]['tuple_sha256'],
                        evaluated_at=now, expires_at=now+100)
        coverage['coverage_sha256'] = digest({k:v for k,v in coverage.items() if k != 'coverage_sha256'})
    value['readiness_sha256'] = digest({k:v for k,v in value.items() if k != 'readiness_sha256'})
    return value


def signed_fixture(record, directory, now=None, inventory=None, snapshot=None, receiving=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    now = int(time.time()) if now is None else now
    source = Path(__file__).resolve().parents[2] / 'contracts/capabilities/definitions-v1.json'
    definition_data = json.loads(source.read_text())
    definition = digest(definition_data)
    scope = record['scope']
    keys = {}
    for role in (('observer', 'reviewer', 'receiver') if receiving else ('observer', 'reviewer')):
        private = directory / (role + '.pem')
        if not private.is_file():
            subprocess.run(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048',
                            '-out', str(private)], check=True, capture_output=True)
            private.chmod(0o600)
        public = subprocess.check_output(['openssl', 'pkey', '-in', str(private), '-pubout'], text=True)
        keys[role] = {'role': role, 'subject_id': 'fixture-' + role, 'public_key_pem': public,
                      'scope': {k: scope[k] for k in ('tenant_id', 'site_id', 'endpoint_id')},
                      'expires_at': now + 7200, 'revoked': False}

    def sign(payload, role):
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()
        signature = subprocess.check_output(['openssl', 'dgst', '-sha256', '-sign',
                                             str(directory / (role + '.pem'))], input=raw)
        return {'key_id': role, 'content_base64': base64.b64encode(raw).decode(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'signature_base64': base64.b64encode(signature).decode()}

    method_modes = {
        'method:' + method['v1_alias'] + ':' + mode: 'unsupported'
        for method in definition_data['methods'].values()
        for mode in definition_data['modes']
    }
    record = copy.deepcopy(record)
    record.pop('verification', None)
    record.update(version=2, evidence_level='E4' if receiving else 'E3',
                  method_modes=method_modes)
    proof = {'kind': 'native_conformance', 'simulation': False, 'finalized': True,
             'scope_sha256': digest(scope), 'definition_sha256': definition,
             'runtime_artifacts': scope['artifacts'], 'adapter_conformant': True,
             'dimensions': record['dimensions'], 'capabilities': record['capabilities'],
             'method_modes': dict(sorted(method_modes.items(), reverse=True)),
             'cases': ({'capability:' + k: 'passed' for k in record['capabilities']}
                       | {'dimension:' + k: 'passed' for k in record['dimensions']}
                       | {'adapter_behavior':'passed','installed_identity':'passed','runtime_artifacts':'passed'}
                       | method_modes),
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
    bundle={'record': record, 'decision': decision, 'evidence': [evidence], 'runtime': runtime}
    if receiving:
        bundle['acceptance']=sign({
            'kind':'operating_acceptance','decision':'accepted','revoked':False,
            'qualification_sha256':decision['sha256'],'record_sha256':digest(record),
            'definition_sha256':definition,'scope_sha256':digest(scope),
            'subject_id':keys['receiver']['subject_id'],
            'observed_at':now,'expires_at':now+3600,
        },'receiver')
    return bundle, keys


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
