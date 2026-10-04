"""Exercise the private P01 Compose installation with synthetic data only."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from local_runtime import prepare

SERVICES = ('console', 'governance', 'catalogue', 'assurance', 'planning', 'inventory', 'lifecycle')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Campaign:
    def __init__(self, root: Path, output: Path, revision: str):
        if output == root or output.is_relative_to(root):
            raise ValueError('Evidence output must be outside the source workspace')
        self.root, self.output, self.revision = root, output, revision
        output.mkdir(parents=True, exist_ok=False)
        self.report = {'schema_version': 1, 'scope': 'Synthetic P01 Compose foundation; no product readiness or native effects', 'source_revision': revision, 'result': 'RUNNING', 'commands': [], 'checks': []}
        self.runtime = Path(tempfile.mkdtemp(prefix='p01-private-parent-')) / 'runtime'
        self.compose: Path | None = None

    def command(self, name: str, argv: list[str], *, data: bytes | None = None, expected: int | None = 0, timeout: int = 120) -> bytes:
        start = time.monotonic()
        timed_out = False
        try:
            result = subprocess.run(argv, cwd=self.root, input=data, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            timed_out = True
            result = subprocess.CompletedProcess(argv,124,error.stdout or b'',(error.stderr or b'')+b'\nBounded command timed out.\n')
        index = len(self.report['commands']) + 1
        entry = {'name': name, 'argv': argv, 'exit_code': result.returncode, 'expected_exit': expected, 'timed_out': timed_out, 'seconds': round(time.monotonic()-start, 3)}
        for key, content in [('stdout', result.stdout), ('stderr', result.stderr)]:
            path = f'{index:03d}-{name}.{key}.log'
            (self.output/path).write_bytes(content)
            entry[key] = {'path': path, 'bytes': len(content), 'sha256': digest(content)}
        self.report['commands'].append(entry)
        self.save()
        if timed_out or (expected is not None and result.returncode != expected):
            raise RuntimeError(f'{name} exited {result.returncode}; inspect retained logs')
        return result.stdout

    def check(self, name: str, condition: bool, observation=None):
        self.report['checks'].append({'name': name, 'passed': bool(condition), 'observation': observation})
        self.save()
        if not condition:
            raise RuntimeError(f'Failed check: {name}')

    def save(self):
        (self.output/'report.json').write_text(json.dumps(self.report, indent=2)+'\n')

    def dc(self, *arguments: str) -> list[str]:
        assert self.compose is not None
        return ['docker', 'compose', '-f', str(self.compose), *arguments]

    def sql(self, service: str, sql: str, *, identity: str = 'runtime', database: str | None = None, expected: int | None = 0, sslmode: str = 'verify-full', bad_password: bool = False) -> bytes:
        # Secret bytes are read only inside the private container and never enter argv/logs.
        password = 'invalid-synthetic-password' if bad_password else f'$(cat /run/secrets/{service}-{identity}-password)'
        script = f'export PGPASSWORD="{password}"; exec psql -X -qAt -v ON_ERROR_STOP=1 "host=postgres port=5432 dbname={database or service} user={service}_{identity} sslmode={sslmode} sslrootcert=/run/secrets/ca.crt connect_timeout=2"'
        return self.command(f'{service}-{identity}-sql', self.dc('exec', '-T', 'postgres', 'sh', '-ec', script), data=sql.encode(), expected=expected, timeout=15)

    def admin(self, sql: str, database: str = 'postgres') -> bytes:
        return self.command('administrator-sql', self.dc('exec', '-T', '--user', 'postgres', 'postgres', 'psql', '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-d', database), data=sql.encode(), timeout=15)

    def request(self, service: str, path: str, token: str | None = None, *, context=None, host: str | None = None):
        headers = {} if token is None else {'Authorization': 'Bearer '+token}
        if host is not None:
            headers['Host'] = host
        request = urllib.request.Request(f'https://localhost:{self.ports[service]}{path}', headers=headers)
        try:
            response = urllib.request.urlopen(request, context=context or self.tls, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.read(65536), dict(response.headers)

    def health(self, service: str, status: int, token: str | None, name: str):
        observed, body, headers = self.request(service, '/health/dependencies', token)
        payload = json.loads(body)
        self.check(name, observed == status and payload.get('scope') == 'foundation_dependencies', {'service': service, 'http_status': observed, 'body': payload, 'cache_control': headers.get('Cache-Control')})

    def wait_health(self, services=SERVICES):
        deadline = time.monotonic()+90
        waiting = set(services)
        while waiting and time.monotonic() < deadline:
            for service in list(waiting):
                try:
                    if self.request(service, '/health/dependencies', self.tokens[service])[0] == 200:
                        waiting.remove(service)
                except (OSError, urllib.error.URLError):
                    pass
            if waiting:
                time.sleep(1)
        self.check('authenticated-dependencies-become-healthy', not waiting, {'unavailable': sorted(waiting)})

    def run(self, images_path: Path | None):
        measured = self.command('source-revision', ['git','rev-parse','HEAD']).decode().strip()
        self.check('exact-source-revision', measured == self.revision)
        status = self.command('source-clean', ['git','status','--porcelain','--untracked-files=all','--','scripts/p01','deploy','services','apps/console'])
        self.check('no-modified-or-untracked-inputs',status.strip() == b'')
        inputs = {}
        for prefix in ('scripts/p01', 'deploy'):
            for path in sorted((self.root/prefix).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts:
                    inputs[str(path.relative_to(self.root))] = digest(path.read_bytes())
        self.report['installation_source_sha256'] = inputs
        if images_path:
            images = json.loads(images_path.read_text())
        else:
            def build(service):
                target = self.output/'images'/service
                try:
                    process = subprocess.run([sys.executable, str(self.root/'scripts/p01/run_images.py'), '--component', service, '--output', str(target), '--source-revision', self.revision], cwd=self.root, capture_output=True, timeout=1200)
                except subprocess.TimeoutExpired as error:
                    (self.output/f'{service}-build-runner.log').write_bytes((error.stdout or b'')+(error.stderr or b'')+b'\nBounded image runner timed out.\n')
                    raise RuntimeError(f'{service} image runner timed out') from error
                (self.output/f'{service}-build-runner.log').write_bytes(process.stdout+process.stderr)
                if process.returncode:
                    raise RuntimeError(f'{service} image verification failed')
                report = json.loads((target/'report.json').read_text())
                return service, report['image']['id']
            with ThreadPoolExecutor(max_workers=3) as pool:
                images = dict(pool.map(build, SERVICES))
        self.report['application_images'] = images
        for service in SERVICES:
            raw = self.command('application-image-identity', ['docker','image','inspect','--format','{{json .Id}} {{json .Os}} {{json .Architecture}} {{json .Config.Labels}}',images[service]]).decode().strip()
            decoder = json.JSONDecoder(); fields = []
            while raw:
                value, end = decoder.raw_decode(raw); fields.append(value); raw = raw[end:].lstrip()
            self.check('owned-image-source-and-platform',len(fields) == 4 and fields[0] == images[service] and fields[1:3] == ['linux','amd64'] and fields[3].get('org.opencontainers.image.revision') == self.revision and fields[3].get('io.product.component') == service,{'service':service,'image_id':fields[0],'labels':fields[3]})
        self.compose = prepare(self.root, self.runtime, images, self.revision)
        rendered = json.loads(self.compose.read_text())
        # Only non-secret rendered configuration and immutable image identities are retained.
        (self.output/'compose.json').write_text(json.dumps(rendered, indent=2)+'\n')
        self.report['configuration_sha256'] = digest(self.compose.read_bytes())
        self.report['project'] = rendered['name']
        self.check('backend-ports-not-published', all(not rendered['services'][s].get('ports') for s in (*SERVICES, 'postgres')))
        self.check('runtime-has-no-migrator-secret', all(not any('migrator' in str(secret) for secret in rendered['services'][s].get('secrets', [])) for s in SERVICES))
        self.command('compose-validation', self.dc('config', '--quiet'))
        self.check('empty-project', self.command('empty-project', self.dc('ps', '-aq')).strip() == b'')
        dependencies = json.loads((self.root/'deploy/dependencies/inputs.lock.json').read_text())
        for name in ('postgres','nginx'):
            self.command('pull-'+name, ['docker','pull','--platform','linux/amd64',dependencies['images'][name]['reference']], timeout=180)
        for service in ('console', 'governance', 'catalogue', 'assurance'):
            name = rendered['name']+'-extract-'+service
            self.command('create-public-extraction', ['docker','create','--name',name,images[service]])
            try:
                self.command('extract-public-root', ['docker','cp', name+':/app/public/.', str(self.runtime/'public'/service)])
            finally:
                self.command('remove-public-extraction', ['docker','rm',name])
        self.command('install-database', self.dc('up','-d','--wait','--wait-timeout','120','postgres'), timeout=180)
        migration = (self.root/'deploy/dependencies/postgres/migrate.sql').read_text()
        for service in SERVICES:
            self.sql(service, f'\\set owner {service}_owner\n\\set runtime {service}_runtime\n'+migration, identity='migrator')
        self.command('install-applications', self.dc('up','-d'), timeout=180)
        self.ports = {}
        for service in SERVICES:
            address = self.command('proxy-port', self.dc('port',service+'-proxy','8443')).decode().strip()
            self.check('proxy-loopback-only', address.startswith('127.0.0.1:'), {'service': service, 'address': address})
            self.ports[service] = int(address.rsplit(':',1)[1])
        self.tokens = {s:(self.runtime/'secrets'/f'{s}-health-token').read_text().strip() for s in SERVICES}
        self.tls = ssl.create_default_context(cafile=str(self.runtime/'secrets/ca.crt'))
        self.wait_health()
        initial_data = {}
        for service in SERVICES:
            self.health(service, 401, None, 'missing-health-identity-denied')
            self.health(service, 401, 'invalid-synthetic-token', 'invalid-health-identity-denied')
            self.health(service, 200, self.tokens[service], 'owned-dependency-health')
            self.check('process-liveness', self.request(service,'/health/live')[0] == 200, service)
            self.check('product-readiness-unavailable', self.request(service,'/health/ready')[0] == 503, service)
            self.check('foreign-host-denied', self.request(service,'/health/live',host='foreign.invalid')[0] == 421, service)
            for path in ('/.env','/composer.json','/config/app.php'):
                self.check('source-outside-public-root', self.request(service,path)[0] == 404, {'service':service,'path':path})
            initial_data[service] = digest(self.sql(service, 'SELECT tenant_id,record_id,payload FROM app.foundation_records ORDER BY tenant_id,record_id;'))
            self.sql(service, "BEGIN; INSERT INTO app.foundation_records VALUES ('tenant_a','runtime-write','synthetic'); ROLLBACK;")
            for sql in ('CREATE TABLE app.forbidden(id integer);','UPDATE app.foundation_schema SET version=2;',f'SET ROLE {service}_owner;'):
                self.sql(service, sql, expected=3)
            foreign = 'catalogue' if service != 'catalogue' else 'governance'
            self.sql(service, 'SELECT 1;', database=foreign, expected=2)
            self.sql(service, 'SELECT 1;', sslmode='disable', expected=2)
            self.sql(service, 'SELECT 1;', bad_password=True, expected=2)
        self.report['initial_fixture_data_sha256'] = initial_data
        # Rotate the service health credential; already-issued values are not cached.
        token_file = self.runtime/'secrets/governance-health-token'
        old_token = self.tokens['governance']; replacement = os.urandom(32).hex()
        token_file.chmod(0o600); token_file.write_text(replacement); token_file.chmod(0o444)
        self.health('governance',401,old_token,'revoked-health-token-denied')
        self.health('governance',200,replacement,'rotated-health-token-accepted')
        self.tokens['governance'] = replacement
        # New database sessions must observe role revocation immediately.
        self.admin('ALTER ROLE governance_runtime NOLOGIN;')
        self.health('governance',503,replacement,'revoked-database-identity-unavailable')
        self.admin('ALTER ROLE governance_runtime LOGIN;')
        self.health('governance',200,replacement,'restored-database-identity-healthy')
        self.sql('planning','SET ROLE planning_owner; UPDATE app.foundation_schema SET version=2;',identity='migrator')
        self.health('planning',503,self.tokens['planning'],'schema-drift-unavailable')
        self.sql('planning','SET ROLE planning_owner; UPDATE app.foundation_schema SET version=1;',identity='migrator')
        self.health('planning',200,self.tokens['planning'],'schema-restored')
        try:
            self.request('console','/health/live',context=ssl.create_default_context())
        except urllib.error.URLError as error:
            self.check('untrusted-ingress-ca-denied', isinstance(error.reason, ssl.SSLCertVerificationError))
        else:
            self.check('untrusted-ingress-ca-denied',False)
        self.command('stop-database',self.dc('stop','postgres'))
        for service in SERVICES:
            self.health(service,503,self.tokens[service],'dependency-loss-unavailable')
            self.check('dependency-loss-keeps-process-live',self.request(service,'/health/live')[0] == 200,service)
        self.command('restart-database',self.dc('up','-d','--wait','--wait-timeout','120','postgres'),timeout=180)
        self.wait_health()
        for service in SERVICES:
            actual = digest(self.sql(service,'SELECT tenant_id,record_id,payload FROM app.foundation_records ORDER BY tenant_id,record_id;'))
            self.check('restart-preserves-fixture-data',actual == initial_data[service],{'service':service,'sha256':actual})
        self.command('installed-inventory',self.dc('ps','--format','json'))
        self.report['result'] = 'PASS'
        self.report['limits'] = ['Synthetic data and diagnostic credentials only; no OIDC/delegated product authority.', 'Product readiness remains unavailable; workers consume no tasks and native endpoints are absent.', 'Database restart is measured; full application/configuration restore, broker/Temporal/evidence storage, Kubernetes and operating acceptance remain unmeasured.']
        self.save()

    def cleanup(self, keep: bool):
        if self.compose is not None:
            try:
                self.command('container-logs',self.dc('logs','--no-color'),expected=None)
            except Exception:
                self.report['container_log_capture_failed'] = True
            if not keep:
                try:
                    self.command('remove-isolated-project',self.dc('down','--volumes','--remove-orphans'))
                    self.report['cleanup_complete'] = True
                except Exception:
                    self.report['cleanup_complete'] = False
                    self.report['result'] = 'FAIL'
                    self.report['cleanup_runtime_preserved'] = str(self.runtime)
                    self.save()
                    raise
        if not keep:
            shutil.rmtree(self.runtime.parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-revision',required=True)
    parser.add_argument('--images',type=Path)
    parser.add_argument('--keep',action='store_true')
    args = parser.parse_args()
    campaign = Campaign(args.workspace.resolve(),args.output.resolve(),args.source_revision)
    try:
        campaign.run(args.images)
    except Exception as error:
        campaign.report['result'] = 'FAIL'
        campaign.report['error'] = str(error)
        raise
    finally:
        try:
            campaign.cleanup(args.keep)
        finally:
            campaign.save()
    print(json.dumps({'result':campaign.report['result'],'checks':len(campaign.report['checks'])}))


if __name__ == '__main__':
    main()
