"""P01.02/P01.06 complete synthetic application and configuration restore campaign."""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.request

from local_runtime import _base, _bind, _openssl, _secret, _write
from permit_desk.bundle import digest, encode, validate_bundle
from run_local import Campaign

SNAPSHOT = """SELECT json_build_object(
'fixture_schema',(SELECT json_agg(t ORDER BY version) FROM app.fixture_schema t),
'tenants',(SELECT json_agg(t ORDER BY tenant_id) FROM app.tenants t),
'permits',COALESCE((SELECT json_agg(t ORDER BY tenant_id,permit_id) FROM app.permits t),'[]'::json),
'attachments',COALESCE((SELECT json_agg(t ORDER BY tenant_id,permit_id) FROM app.attachments t),'[]'::json));"""


def prepare_fixture(root, directory, image, revision, config):
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Unpinned fixture inputs')
    directory.mkdir(mode=0o700, exist_ok=False)
    private = directory/'secrets'
    private.mkdir(mode=0o700)
    _write(directory/'config.json', json.dumps(config, indent=2)+'\n')
    for name in ('postgres-password', 'runtime-password', 'migrator-password', 'backup-password', *config['principals']):
        _write(private/name, secrets.token_urlsafe(32)+'\n')
    _openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
             '-keyout', str(private/'ca.key'), '-out', str(private/'ca.crt'), '-days', '2', '-sha256',
             '-subj', '/CN=Permit Desk disposable CA', '-addext', 'basicConstraints=critical,CA:TRUE',
             '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    (private/'ca.key').chmod(0o400)
    (private/'ca.crt').chmod(0o444)
    for name, san in (('web', 'DNS:localhost,IP:127.0.0.1'), ('postgres', 'DNS:postgres')):
        _write(private/f'{name}.ext', 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName='+san+'\n')
        _openssl('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes', '-keyout', str(private/f'{name}.key'), '-out', str(private/f'{name}.csr'), '-subj', '/CN='+name)
        _openssl('x509', '-req', '-in', str(private/f'{name}.csr'), '-CA', str(private/'ca.crt'), '-CAkey', str(private/'ca.key'), '-set_serial', str(secrets.randbits(128)+1), '-days', '2', '-sha256', '-extfile', str(private/f'{name}.ext'), '-out', str(private/f'{name}.crt'))
        for suffix in ('crt', 'key'):
            (private/f'{name}.{suffix}').chmod(0o444)
        for suffix in ('csr', 'ext'):
            (private/f'{name}.{suffix}').unlink()
    dependency = json.loads((root/'deploy/dependencies/inputs.lock.json').read_text())['images']['postgres']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', dependency['digest']) or dependency['reference'] != 'docker.io/library/postgres@'+dependency['digest']:
        raise ValueError('Unpinned database input')
    definitions = root/'deploy/fixtures/permit-desk'
    app = {**_base(image), 'user': '10001:10001', 'networks': ['database', 'ingress'],
           'mem_limit': '256m', 'cpus': 1, 'pids_limit': 64,
           'volumes': [_bind(directory/'config.json', '/run/config/config.json'), 'attachments:/attachments'],
           'secrets': [_secret(n) for n in ('runtime-password', 'ca.crt', 'web.crt', 'web.key', *config['principals'])],
           'ports': [{'target': 8443, 'published': '0', 'host_ip': '127.0.0.1', 'protocol': 'tcp'}]}
    postgres = {**_base(dependency['reference']), 'networks': ['database'], 'user': '0:0',
                'cap_add': ['CHOWN', 'DAC_OVERRIDE', 'FOWNER', 'SETGID', 'SETUID'],
                'mem_limit': '512m', 'cpus': 1, 'pids_limit': 128,
                'entrypoint': ['/bin/bash', '/fixture/postgres.sh'],
                'tmpfs': ['/tmp:mode=1777', '/var/run/postgresql:mode=1777'],
                'volumes': ['database:/var/lib/postgresql', _bind(definitions/'postgres.sh', '/fixture/postgres.sh'),
                            _bind(definitions/'initialize.sh', '/docker-entrypoint-initdb.d/10-permit-desk.sh')],
                'secrets': [_secret(n) for n in ('postgres-password', 'runtime-password', 'migrator-password', 'backup-password', 'ca.crt', 'postgres.crt', 'postgres.key')],
                'healthcheck': {'test': ['CMD-SHELL', 'pg_isready -h 127.0.0.1 -U postgres -d postgres'], 'interval': '1s', 'timeout': '3s', 'retries': 60}}
    compose = {'name': 'p01-permit-'+secrets.token_hex(6), 'services': {'app': app, 'postgres': postgres},
               'networks': {'database': {'internal': True}, 'ingress': {'driver': 'bridge', 'driver_opts': {'com.docker.network.bridge.enable_ip_masquerade': 'false'}}},
               'volumes': {'database': {}, 'attachments': {}},
               'secrets': {p.name: {'file': str(p)} for p in private.iterdir() if p.name != 'ca.key'}}
    path = directory/'compose.json'
    path.write_text(json.dumps(compose, indent=2)+'\n')
    return path


class PermitCampaign(Campaign):
    def __init__(self, root, output, revision):
        super().__init__(root, output, revision)
        self.report.update(scope='Synthetic Permit Desk application/configuration recovery; no native effects', started_at=datetime.now(timezone.utc).isoformat())
        self.stacks = {}
        self.config = json.loads((root/'deploy/fixtures/permit-desk/config.json').read_text())

    def select(self, name):
        self.compose = self.stacks[name]
        self.runtime = self.compose.parent
        self.tls = ssl.create_default_context(cafile=str(self.runtime/'secrets/ca.crt'))

    def install(self, name, bundle=None, capture_digest=None):
        # No destination, volume, database or secret exists until admission succeeds.
        archive = None if bundle is None else validate_bundle(bundle, capture_digest, self.image, self.revision, self.config)
        directory = self.runtime.parent/name if not self.stacks else next(iter(self.stacks.values())).parent.parent/name
        self.stacks[name] = prepare_fixture(self.root, directory, self.image, self.revision, self.config if bundle is None else bundle['config'])
        self.select(name)
        self.command(name+'-compose-valid', self.dc('config', '--quiet'))
        self.check(name+'-empty-installation', not self.command(name+'-empty-project', self.dc('ps', '-aq')).strip())
        rendered = json.loads(self.compose.read_text())
        self.check(name+'-runtime-identity-isolation', {s['source'] for s in rendered['services']['app']['secrets']} == {'runtime-password', 'ca.crt', 'web.crt', 'web.key', 'writer_a', 'reader_a', 'writer_b'} and not rendered['services']['postgres'].get('ports'))
        (self.output/(name+'-compose.json')).write_text(json.dumps(rendered, indent=2)+'\n')
        self.command(name+'-database-install', self.dc('up', '-d', '--wait', '--wait-timeout', '120', 'postgres'), timeout=180)
        self.check(name+'-schema-absent', self.admin("SELECT count(*) FROM pg_namespace WHERE nspname='app';").strip() == b'0')
        if archive is None:
            self.database('migrator', (self.root/'deploy/fixtures/permit-desk/schema.sql').read_bytes())
        else:
            self.database('migrator', archive, program='pg_restore', arguments=['--no-owner', '--no-privileges', '--single-transaction', '--exit-on-error', '--role=pd_owner'])
            self.files('import', bundle['attachments'])
        self.database('migrator', (self.root/'deploy/fixtures/permit-desk/grants.sql').read_bytes())
        if bundle is not None:
            self.check(name+'-full-logical-state-equality', self.snapshot() == bundle['snapshot'], self.snapshot())
            self.check(name+'-full-attachment-equality', self.files('export') == bundle['attachments'])
            self.check(name+'-configuration-equality', json.loads((self.runtime/'config.json').read_text()) == bundle['config'], {'sha256': digest((self.runtime/'config.json').read_bytes())})
        self.start(name)

    def start(self, name):
        self.command(name+'-start-application', self.dc('up', '-d', 'app'))
        address = self.command(name+'-https-port', self.dc('port', 'app', '8443')).decode().strip()
        self.check(name+'-loopback-ingress', address.startswith('127.0.0.1:'), address)
        self.port = int(address.rsplit(':', 1)[1])
        deadline = time.monotonic()+30
        while time.monotonic() < deadline:
            try:
                if self.http('/health/live')[0] == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.25)
        else:
            raise RuntimeError('Fixture application did not become live')
        self.assert_http(name+'-native-writes-disabled', '/health/live', 200)

    def database(self, identity, data, *, program='psql', arguments=(), expected=0):
        # Passwords are read inside the container; stdout never contains secrets.
        command = f'export PGPASSWORD="$(cat /run/secrets/{identity}-password)"; exec {program} '
        if program == 'psql':
            command += '-X -qAt -v ON_ERROR_STOP=1 '
        command += ' '.join(arguments)
        command += f' --dbname="host=postgres dbname=permit_desk user=pd_{identity} sslmode=verify-full sslrootcert=/run/secrets/ca.crt connect_timeout=2"'
        return self.command(identity+'-'+program, self.dc('exec', '-T', 'postgres', 'sh', '-ec', command), data=data, expected=expected, timeout=30)

    def admin(self, sql, database='permit_desk'):
        return super().admin(sql, database)

    def snapshot(self):
        return json.loads(self.database('backup', SNAPSHOT.encode()))

    def files(self, operation, entries=None):
        raw = self.command('attachments-'+operation, self.dc('run', '--rm', '--no-deps', '-T', '--entrypoint', 'python', 'app', '/app/state.py', operation), data=None if entries is None else encode(entries))
        return json.loads(raw)

    def http(self, path, principal=None, data=None, token=None):
        headers = {}
        if principal:
            token = (self.runtime/'secrets'/principal).read_text().strip()
        if token:
            headers['Authorization'] = 'Bearer '+token
        if data is not None:
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(f'https://localhost:{self.port}'+path, data=None if data is None else encode(data), headers=headers)
        try:
            response = urllib.request.urlopen(request, context=self.tls, timeout=7)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read(500_001)
            if len(raw) > 500_000:
                raise ValueError('Oversize fixture response')
            return response.status, json.loads(raw)

    def assert_http(self, name, path, status, principal=None, data=None, token=None):
        code, body = self.http(path, principal, data, token)
        self.check(name, code == status and (path != '/health/live' or body.get('native_writes') is False), {'status': code, 'body': body})
        return body

    def create(self, marker, principal='writer_a', tenant='t_demo'):
        content = ('Synthetic attachment for '+tenant+'/'+marker+'\n').encode()
        body = {'permit_id': marker, 'title': 'Synthetic '+marker, 'attachment_base64': base64.b64encode(content).decode()}
        self.assert_http('application-write-'+marker, f'/api/tenants/{tenant}/permits', 201, principal, body)
        found = self.assert_http('application-read-'+marker, f'/api/tenants/{tenant}/permits/{marker}/attachment', 200, principal)['permits']
        self.check('attachment-bytes-'+marker, len(found) == 1 and found[0]['attachment_base64'] == body['attachment_base64'])
        return body

    def capture(self, name):
        self.command(name+'-stop-all-application-writers', self.dc('stop', '-t', '10', 'app'))
        self.check(name+'-application-stopped', not self.command('running-app', self.dc('ps', '--status', 'running', '-q', 'app')).strip())
        self.admin("ALTER ROLE pd_runtime NOLOGIN; SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename='pd_runtime';")
        self.check(name+'-no-runtime-sessions', self.admin("SELECT count(*) FROM pg_stat_activity WHERE usename='pd_runtime';").strip() == b'0')
        self.database('runtime', b'SELECT 1;', expected=2)
        snapshot = self.snapshot()
        archive = self.database('backup', None, program='pg_dump', arguments=['--format=custom', '--no-owner', '--no-acl', '--schema=app'])
        attachments = self.files('export')
        bundle = {'schema_version': 1, 'fixture': 'permit-desk-v1', 'source_revision': self.revision, 'image_id': self.image,
                  'config': json.loads((self.runtime/'config.json').read_text()), 'snapshot': snapshot,
                  'database': {'base64': base64.b64encode(archive).decode(), 'sha256': digest(archive), 'bytes': len(archive)},
                  'attachments': attachments, 'writers': {'application': 'stopped', 'runtime_login': 'disabled', 'runtime_sessions': 0, 'other_writers': []}}
        checksum = digest(encode(bundle))
        validate_bundle(bundle, checksum, self.image, self.revision, self.config)
        self.check(name+'-capture-state-unchanged', self.snapshot() == snapshot and self.files('export') == attachments)
        (self.output/(name+'-bundle.json')).write_bytes(encode(bundle))
        self.report.setdefault('captures', {})[name] = {'sha256': checksum, 'permits': len(snapshot['permits']), 'attachments': len(attachments), 'archive_bytes': len(archive)}
        self.save()
        return bundle, checksum

    def rejected_captures(self, bundle, checksum):
        mutations = {}
        mutations['corrupt-database'] = copy.deepcopy(bundle)
        mutations['corrupt-database']['database']['base64'] = base64.b64encode(b'PGDMPcorrupt').decode()
        mutations['missing-attachment'] = copy.deepcopy(bundle)
        mutations['missing-attachment']['attachments'].pop()
        mutations['unsafe-configuration'] = copy.deepcopy(bundle)
        mutations['unsafe-configuration']['config']['native_writes'] = True
        mutations['unfenced-writer'] = copy.deepcopy(bundle)
        mutations['unfenced-writer']['writers']['runtime_login'] = 'enabled'
        mutations['wrong-image'] = copy.deepcopy(bundle)
        mutations['wrong-image']['image_id'] = 'sha256:'+'0'*64
        mutations['stale-digest'] = copy.deepcopy(bundle)
        mutations['stale-digest']['snapshot']['permits'][0]['title'] = 'Changed'
        for name, changed in mutations.items():
            before = set(self.stacks)
            try:
                self.install('rejected-'+name, changed, checksum if name == 'stale-digest' else digest(encode(changed)))
            except ValueError as error:
                self.check('reject-'+name, set(self.stacks) == before, {'reason': str(error), 'destination_allocated': False})
            else:
                raise RuntimeError('Invalid capture admitted: '+name)

    def run(self):
        self.check('exact-source', self.command('source', ['git', 'rev-parse', 'HEAD']).decode().strip() == self.revision)
        prefixes = ['scripts/p01', 'deploy/fixtures/permit-desk', 'deploy/dependencies/inputs.lock.json', '.github/workflows/p01-permit-desk-recovery.yml']
        self.check('clean-inputs', not self.command('source-clean', ['git', 'status', '--porcelain', '--untracked-files=all', '--', *prefixes]).strip())
        self.report['source_sha256'] = {str(p.relative_to(self.root)): digest(p.read_bytes()) for prefix in prefixes for p in ([self.root/prefix] if (self.root/prefix).is_file() else sorted((self.root/prefix).rglob('*'))) if p.is_file() and '__pycache__' not in p.parts}
        self.command('docker-version', ['docker', 'version'])
        self.command('compose-version', ['docker', 'compose', 'version'])
        iid = self.output/'image-id.txt'
        self.command('build-fixture', ['docker', 'build', '--platform', 'linux/amd64', '--build-arg', 'SOURCE_REVISION='+self.revision, '--iidfile', str(iid), str(self.root/'scripts/p01/permit_desk')], timeout=600)
        self.image = iid.read_text().strip()
        info = json.loads(self.command('image-identity', ['docker', 'image', 'inspect', self.image]))[0]
        self.check('owned-immutable-image', info['Id'] == self.image and info['Os'] == 'linux' and info['Architecture'] == 'amd64' and info['Config']['Labels']['org.opencontainers.image.revision'] == self.revision and info['Config']['Labels']['io.product.component'] == 'permit-desk-fixture')
        self.report['image_id'] = self.image
        db_image = json.loads((self.root/'deploy/dependencies/inputs.lock.json').read_text())['images']['postgres']['reference']
        self.command('pull-pinned-postgres', ['docker', 'pull', '--platform', 'linux/amd64', db_image], timeout=180)
        self.command('postgres-image-identity', ['docker', 'image', 'inspect', db_image])
        self.install('source')
        self.command('database-versions', self.dc('exec', '-T', 'postgres', 'sh', '-ec', 'postgres --version; pg_dump --version; pg_restore --version'))
        self.command('application-versions', self.dc('exec', '-T', 'app', 'python', '-c', 'import sys,importlib.metadata as m; print(sys.version); print({n:m.version(n) for n in ("psycopg","psycopg-binary","typing-extensions")})'))
        for principal, tenant in [('writer_a', 't_demo'), ('writer_b', 't_other')]:
            for marker in ('permit_one', 'permit_two'):
                body = self.create(marker, principal, tenant)
        before = self.snapshot()
        path = '/api/tenants/t_demo/permits'
        self.assert_http('anonymous-denied', path, 401)
        self.assert_http('invalid-identity-denied', path, 401, token='invalid-synthetic-token')
        self.assert_http('foreign-tenant-list-denied', '/api/tenants/t_other/permits', 403, 'writer_a')
        self.assert_http('foreign-attachment-denied', '/api/tenants/t_other/permits/permit_one/attachment', 403, 'writer_a')
        self.assert_http('reader-write-denied', path, 403, 'reader_a', body)
        self.assert_http('forged-tenant-field-denied', path, 422, 'writer_a', {**body, 'tenant_id': 't_other'})
        self.assert_http('duplicate-write-conflict', path, 409, 'writer_a', body)
        self.check('denials-preserve-all-records', self.snapshot() == before)
        self.database('runtime', b'CREATE TABLE app.forbidden(id integer);', expected=3)
        self.database('runtime', b'SET ROLE pd_owner;', expected=3)
        self.database('backup', b"INSERT INTO app.permits VALUES ('t_demo','forbidden','Forbidden',now());", expected=3)
        source_token = (self.runtime/'secrets/writer_a').read_text().strip()
        initial, initial_digest = self.capture('source')
        self.rejected_captures(initial, initial_digest)
        started = time.monotonic()
        self.install('target', initial, initial_digest)
        self.report['initial_restore_seconds'] = round(time.monotonic()-started, 3)
        self.assert_http('source-credential-not-transferred', path, 401, token=source_token)
        self.assert_http('restored-reader-access', path, 200, 'reader_a')
        self.assert_http('restored-foreign-tenant-denied', '/api/tenants/t_other/permits', 403, 'writer_a')
        self.create('known_target_write')
        target_snapshot = self.snapshot()
        # Rehearse a rejected application configuration rollout, then restore the
        # captured configuration and exact image without rebuilding or reseeding.
        config_path = self.runtime/'config.json'
        bad = {**self.config, 'schema_version': 999}
        config_path.chmod(0o600); config_path.write_bytes(encode(bad)); config_path.chmod(0o444)
        self.command('invalid-rollout-restart', self.dc('restart', 'app'))
        container = self.command('application-container', self.dc('ps', '-a', '-q', 'app')).decode().strip()
        exit_code = self.command('rejected-rollout-exit', ['docker', 'wait', container], timeout=30).strip()
        self.check('invalid-configuration-rejects-boot', exit_code != b'0', {'exit_code': exit_code.decode()})
        rollback_start = time.monotonic()
        config_path.chmod(0o600); config_path.write_bytes(encode(initial['config'])); config_path.chmod(0o444)
        self.start('rollback')
        self.assert_http('rollback-keeps-target-write', path+'/known_target_write', 200, 'writer_a')
        self.check('rollback-keeps-complete-state', self.snapshot() == target_snapshot)
        self.report['configuration_rollback_seconds'] = round(time.monotonic()-rollback_start, 3)
        self.command('dependency-outage', self.dc('stop', 'postgres'))
        self.assert_http('outage-application-unavailable', path, 503, 'writer_a')
        self.assert_http('outage-process-live', '/health/live', 200)
        self.command('dependency-restart', self.dc('up', '-d', '--wait', '--wait-timeout', '120', 'postgres'), timeout=180)
        self.assert_http('dependency-recovered', path, 200, 'writer_a')
        self.check('restart-keeps-target-write', self.snapshot() == target_snapshot)
        post, post_digest = self.capture('target')
        self.select('source')
        self.check('source-is-stale-after-target-write', all(p['permit_id'] != 'known_target_write' for p in self.snapshot()['permits']))
        self.database('runtime', b'SELECT 1;', expected=2)
        self.install('recovery', post, post_digest)
        self.assert_http('post-write-restore-keeps-marker', path+'/known_target_write/attachment', 200, 'writer_a')
        self.create('known_recovery_write')
        self.report['result'] = 'PASS'
        self.report['limits'] = ['Synthetic single-writer HTTP application, disposable TLS and file-backed credentials; no production identity or guest deployment.', 'Complete app/configuration/database/attachment restore uses a readable quiesced source or target on the same PostgreSQL patch.', 'Compose only; no Kubernetes fixture restore, object-store recovery, external alert acknowledgement, promotion trust or native qualification.', 'Digests bind retained bytes; no capture signature or untrusted-archive safety claim. G01 and product readiness remain unaccepted.']
        self.save()

    def cleanup_all(self):
        parent = self.runtime.parent
        all_removed = True
        for name in self.stacks:
            self.select(name)
            try:
                self.command(name+'-logs', self.dc('logs', '--no-color', '--tail', '100'), expected=None)
            except Exception:
                self.report.setdefault('log_collection_failures', []).append(name)
            try:
                self.command(name+'-remove-owned-installation', self.dc('down', '--volumes', '--remove-orphans'))
                self.check(name+'-no-remaining-containers', not self.command(name+'-removed', self.dc('ps', '-aq')).strip())
            except Exception:
                all_removed = False
                self.report['result'] = 'FAIL'
        self.report['cleanup_complete'] = all_removed
        if all_removed:
            shutil.rmtree(parent)
        else:
            self.report['private_runtime_preserved'] = str(parent)
        self.report['finished_at'] = datetime.now(timezone.utc).isoformat()
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-revision', required=True)
    args = parser.parse_args()
    campaign = PermitCampaign(args.workspace.resolve(), args.output.resolve(), args.source_revision)
    try:
        campaign.run()
    except Exception as error:
        campaign.report.update(result='FAIL', error=str(error))
        raise
    finally:
        campaign.cleanup_all()
    if campaign.report['result'] != 'PASS':
        raise RuntimeError('Recovery campaign or cleanup failed')
    print(json.dumps({'result': 'PASS', 'checks': len(campaign.report['checks'])}))


if __name__ == '__main__':
    main()
