#!/usr/bin/env python3
"""P05 disposable PostgreSQL, TLS API, confirmed broker and compiled browser campaign."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from jsonschema import Draft202012Validator
from openapi_schema_validator import OAS31Validator
from openapi_spec_validator import validate_spec
import importlib.util
ops_spec=importlib.util.spec_from_file_location('inventory_operations',Path(__file__).resolve().parents[1]/'p04/generated_operations.py')
ops_module=importlib.util.module_from_spec(ops_spec);ops_spec.loader.exec_module(ops_module)
OPERATIONS=ops_module.OPERATIONS
from live_fixture import NativePeer, TlsProxy
from live_campaign import campaign


def main(extension=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('P05_TEST_POSTGRES') != '1':
        parser.error('Requires the disposable P05 GitHub Actions service.')
    engine = os.environ.get('P05_BROWSER_ENGINE', 'chromium')
    if engine not in ['chromium', 'firefox', 'webkit']:
        parser.error('Unsupported browser.')
    root = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'result': 'RUNNING', 'source_revision': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
        'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'], 'browser_engine': engine, 'observed_at': datetime.datetime.now(datetime.UTC).isoformat(),
        'checks': [], 'commands': [], 'limitations': ['Synthetic OIDC transport used only by the separate principal bootstrap process; live requests use real Governance current authority.',
            'Controlled Inventory contract observations and synthetic qualification-shaped records test E2 integration; they confer no native or operational support.',
            'Native APIs are synthetic HTTPS peers; no installed VMware or OpenStack E3 qualification.',
            'TLS application peers terminate at disposable loopback forwarding proxies; no operated ingress qualification.',
            'Automated browser checks do not establish representative operator, screen-reader or independent G05 receiving acceptance.']}
    paths = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
    report['source_sha256'] = {n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths if n.startswith(('services/planning/', 'services/lifecycle/', 'services/assurance/', 'services/inventory/', 'workers/inventory/', 'workers/lifecycle/', 'scripts/p06/', '.github/workflows/p06', 'services/governance/', 'services/catalogue/', 'apps/console/', 'contracts/', 'scripts/p03/seed_', 'scripts/p04/', 'scripts/p05/', '.github/workflows/p05', 'deploy/dependencies/stateful/inventory-facts.json'))}
    private_values = [os.environ['P05_ADMIN_PASSWORD']]
    processes, handles, proxies = {}, [], []
    broker = None
    envs = {}

    def redact(s):
        for value in private_values:
            s = s.replace(value, '[REDACTED]')
        return s

    def check(name, passed):
        report['checks'].append({'name': name, 'passed': bool(passed)})
        if not passed:
            raise RuntimeError(name)

    def run(command, *, cwd=root, env=None, data=None, expected=0, label=None):
        if command[0] == 'php':
            command = [command[0], '-d', 'zend.exception_ignore_args=On', *command[1:]]
        result = subprocess.run(command, cwd=cwd, env=env, input=data, text=True, capture_output=True, timeout=240)
        if label:
            body = redact(result.stdout+result.stderr)
            (out/(label+'.log')).write_text(body)
            report['commands'].append({'name': label, 'exit_code': result.returncode, 'sha256': hashlib.sha256(body.encode()).hexdigest()})
        if result.returncode != expected:
            raise RuntimeError((label or command[0])+' failed: '+redact((result.stdout+result.stderr)[-3000:]))
        return result.stdout

    pg_env = os.environ | {'PGHOST': '127.0.0.1', 'PGPORT': '5432', 'PGUSER': 'postgres', 'PGPASSWORD': private_values[0]}

    def sql(statement, database='postgres', user='postgres', password=None):
        return run(['psql', '-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-d', database], env=pg_env | {'PGUSER': user, 'PGPASSWORD': password or pg_env['PGPASSWORD']}, data=statement).strip()

    def stop(name):
        process = processes.pop(name, None)
        if process and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)

    @contextmanager
    def private_directory():
        with tempfile.TemporaryDirectory(prefix='p05-live-') as directory:
            try:
                yield directory
            finally:
                for name in ['governance', 'catalogue', 'console', 'inventory', 'planning', 'assurance']:
                    log = Path(directory)/(name+'.log')
                    if log.exists():
                        (out/(name+'-http.log')).write_text(redact(log.read_text()))
                browser_file = root/'apps/console/test-results/p05-browser.json'
                if browser_file.exists():
                    (out/'browser.json').write_text(redact(browser_file.read_text()))

    try:
        api = json.loads((root/'contracts/openapi/inventory-v1.1.json').read_text())
        validate_spec(api)
        check('independent-openapi-specification-validation', True)
        run(['python', 'scripts/p04/generate_clients.py', '--check'], label='generated-clients')
        with private_directory() as directory:
            private = Path(directory)
            certificate, key = private/'services.crt', private/'services.key'
            run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key), '-out', str(certificate), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost'])
            container = os.environ['P05_POSTGRES_CONTAINER']
            check('disposable-postgres-container', re.fullmatch('[0-9a-f]{64}', container) is not None)
            run(['docker', 'exec', container, 'mkdir', '-p', '/tmp/p03-tls'])
            for file in [certificate, key]:
                run(['docker', 'cp', str(file), container+':/tmp/p03-tls/'+file.name])
            run(['docker', 'exec', container, 'chown', '-R', 'postgres:postgres', '/tmp/p03-tls'])
            run(['docker', 'exec', container, 'chmod', '0600', '/tmp/p03-tls/services.key'])
            sql("ALTER SYSTEM SET ssl_cert_file='/tmp/p03-tls/services.crt'; ALTER SYSTEM SET ssl_key_file='/tmp/p03-tls/services.key'; ALTER SYSTEM SET ssl='on'; SELECT pg_reload_conf();")
            pg_env.update(PGSSLMODE='verify-full', PGSSLROOTCERT=str(certificate))
            time.sleep(.3)
            check('postgres-verified-tls', sql('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid();') == 't')
            credentials = {}
            for name in ['console-governance', 'catalogue-governance', 'console-catalogue', 'inventory-governance', 'console-inventory', 'worker-inventory', 'native-token', 'planning-governance', 'assurance-governance', 'console-planning', 'planning-catalogue', 'planning-inventory', 'planning-assurance', 'governance-planning']:
                value = secrets.token_hex(32)
                private_values.append(value)
                file = private/name
                file.write_text(value)
                file.chmod(0o600)
                credentials[name] = (value, str(file))
            admission = private/'identity-admission.json'
            admission.write_text(json.dumps({'version': 1, 'installation_id': str(uuid.uuid4()), 'epoch': secrets.token_hex(32), 'state': 'active', 'bootstrap_allowed': True}))
            admission.chmod(0o600)
            directories = {'governance': 'services/governance', 'catalogue': 'services/catalogue', 'console': 'apps/console', 'inventory': 'services/inventory', 'planning':'services/planning', 'assurance':'services/assurance'}
            for name, relative in directories.items():
                password, migrator = secrets.token_hex(32), secrets.token_hex(32)
                private_values.extend([password, migrator])
                password_file = private/(name+'-database')
                password_file.write_text(password)
                password_file.chmod(0o600)
                sql(f"CREATE ROLE {name}_owner NOLOGIN; CREATE ROLE {name}_runtime LOGIN NOINHERIT PASSWORD '{password}'; CREATE ROLE {name}_migrator LOGIN NOINHERIT PASSWORD '{migrator}'; GRANT {name}_owner TO {name}_migrator WITH INHERIT FALSE, SET TRUE; CREATE DATABASE {name} OWNER {name}_owner;")
                sql(f'REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {name}_runtime,{name}_migrator; REVOKE ALL ON SCHEMA public FROM PUBLIC; CREATE SCHEMA app AUTHORIZATION {name}_owner; GRANT USAGE ON SCHEMA app TO {name}_runtime;', name)
                # Governance/Console P02 migrations refine these existing baseline grants;
                # Catalogue uses only its explicit column-level grants.
                if name not in {'catalogue', 'inventory', 'planning'}:
                    sql(f'ALTER DEFAULT PRIVILEGES FOR ROLE {name}_owner IN SCHEMA app GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO {name}_runtime;', name)
                for migration in sorted((root/relative/('migrations' if name in {'inventory','planning'} else 'database/migrations')).glob('*.sql')):
                    contents = ('SET ROLE inventory_owner;\n' if name == 'inventory' else '')+migration.read_text()
                    sql(contents, name, name+'_migrator', migrator)
                    if name == 'inventory' or migration.name == '012_inventory_delegation.sql':
                        sql(contents, name, name+'_migrator', migrator)
                app_key = 'base64:'+base64.b64encode(secrets.token_bytes(32)).decode()
                private_values.append(app_key)
                envs[name] = os.environ | {'APP_ENV': 'p05-verification', 'P03_TEST_POSTGRES': '1', 'APP_DEBUG': 'false', 'APP_KEY': app_key,
                    'DB_HOST': '127.0.0.1', 'DB_PORT': '5432', 'DB_DATABASE': name, 'DB_USERNAME': name+'_runtime', 'DB_PASSWORD': password,
                    'DB_PASSWORD_FILE': str(password_file), 'DB_SSLMODE': 'verify-full', 'DB_SSLROOTCERT': str(certificate),
                    'GOVERNANCE_URL': 'https://127.0.0.1:8442', 'GOVERNANCE_CA_FILE': str(certificate), 'GOVERNANCE_CREDENTIAL_FILE': credentials['catalogue-governance'][1],
                    'CONSOLE_CREDENTIAL_FILE': credentials['console-governance'][1], 'CATALOGUE_GOVERNANCE_CREDENTIAL_FILE': credentials['catalogue-governance'][1],
                    'CONSOLE_CATALOGUE_CREDENTIAL_FILE': credentials['console-catalogue'][1], 'CATALOGUE_CONSOLE_CREDENTIAL_FILE': credentials['console-catalogue'][1],
                    'INVENTORY_URL': 'https://127.0.0.1:8444', 'INVENTORY_CA_FILE': str(certificate),
                    'INVENTORY_GOVERNANCE_CREDENTIAL_FILE': credentials['inventory-governance'][1], 'INVENTORY_CONSOLE_CREDENTIAL_FILE': credentials['console-inventory'][1], 'CONSOLE_INVENTORY_CREDENTIAL_FILE': credentials['console-inventory'][1],
                    'CATALOGUE_URL': 'https://127.0.0.1:8443', 'CATALOGUE_CA_FILE': str(certificate), 'GOVERNANCE_IDENTITY_ADMISSION_FILE': str(admission),
                    'SESSION_DRIVER': 'database', 'CACHE_STORE': 'database', 'SESSION_SECURE_COOKIE': 'false', 'APP_URL': 'http://127.0.0.1:8031', 'PHP_CLI_SERVER_WORKERS': '4'}
                envs[name].update(PLANNING_URL='https://127.0.0.1:8446',PLANNING_CA_FILE=str(certificate),PLANNING_CREDENTIAL_FILE=credentials['console-planning'][1],PLANNING_CONSOLE_CREDENTIAL_FILE=credentials['console-planning'][1],PLANNING_GOVERNANCE_CREDENTIAL_FILE=credentials['planning-governance'][1],ASSURANCE_GOVERNANCE_CREDENTIAL_FILE=credentials['assurance-governance'][1],PLANNING_GOVERNANCE_READER_CREDENTIAL_FILE=credentials['governance-planning'][1],PLANNING_CATALOGUE_CREDENTIAL_FILE=credentials['planning-catalogue'][1],PLANNING_INVENTORY_CREDENTIAL_FILE=credentials['planning-inventory'][1],PLANNING_ASSURANCE_CREDENTIAL_FILE=credentials['planning-assurance'][1],INVENTORY_PLANNING_CREDENTIAL_FILE=credentials['planning-inventory'][1],ASSURANCE_URL='https://127.0.0.1:8447',ASSURANCE_CA_FILE=str(certificate))
                if name in {'catalogue','assurance'}:envs[name]['PLANNING_CALLER_CREDENTIAL_FILE']=credentials['planning-'+name][1]
                if name=='assurance':envs[name]['GOVERNANCE_CREDENTIAL_FILE']=credentials['assurance-governance'][1]
                if name=='governance':envs[name]['PLANNING_CREDENTIAL_FILE']=credentials['governance-planning'][1]
            fixture_file = private/'browser.json'
            run(['php', 'scripts/p05/seed_governance.php', str(fixture_file)], env=envs['governance'], label='seed-principals')
            fixture = json.loads(fixture_file.read_text())
            private_values += [fixture['admin_token'], fixture['author_token'], fixture['foreign_token'],fixture['operator_token'],fixture['reviewer_token']]
            run(['php', 'scripts/p03/seed_console.php', str(fixture_file)], env=envs['console'], label='seed-browser-sessions')
            check('both-independent-browser-sessions-persisted', sql('SELECT count(*) FROM app.sessions;', 'console') == '2')
            fixture = json.loads(fixture_file.read_text())
            private_values += [fixture['admin_cookie']['value'], fixture['author_cookie']['value']]
            fault_file = private/'lose-next-response.json'
            for port, upstream, fault in [(8442, 8032, None), (8443, 8033, None), (8444, 8034, None), (8446,8035,fault_file), (8447,8036,None)]:
                proxies.append(TlsProxy(port, upstream, certificate, key, fault))

            def start(name):
                port = {'governance': 8032, 'catalogue': 8033, 'console': 8031, 'inventory': 8034, 'planning':8035, 'assurance':8036}[name]
                directory = root/directories[name]
                handle = (private/(name+'.log')).open('ab')
                handles.append(handle)
                router = directory/'vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php'
                command = [str(root/f'services/{name}/.venv/bin/{name}-serve'), '--host', '127.0.0.1', '--port', str(port)] if name in {'inventory','planning'} else ['php', '-S', '127.0.0.1:'+str(port), str(router)]
                processes[name] = subprocess.Popen(command, cwd=directory if name in {'inventory','planning'} else directory/'public', env=envs[name], stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic()+15
                while True:
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/health/live', timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        if time.monotonic() > deadline or processes[name].poll() is not None:
                            raise RuntimeError(name+'_start_failed')
                        time.sleep(.1)

            owner = sql("SELECT actor_id FROM app.tenant_memberships WHERE tenant_id='"+fixture['tenant']+"' AND role='tenant_admin' AND state='active';", 'governance')
            check('independent-site-owner-resolved', re.fullmatch('[0-9a-f-]{36}', owner) is not None)
            site, worker_id = str(uuid.uuid4()), str(uuid.uuid4())
            policy = {
                'policy_id': str(uuid.uuid4()), 'tenant': fixture['tenant'], 'site': site,
                'owner': owner, 'worker': worker_id, 'epoch': str(uuid.uuid4()),
                'worker_fingerprint': hashlib.sha256(credentials['worker-inventory'][0].encode()).hexdigest(),
                'platform': 'openstack', 'native_scope': 'project-a', 'authority': 'synthetic-native',
                'installed': {'product': 'synthetic-only', 'api': 'explicit-test-versions', 'backend': 'unassessed', 'features': [], 'entitlements': [], 'configuration_reference': 'p04-e2-fixture'},
                'streams': [{'kind': kind, 'base_url': 'https://127.0.0.1:8445'+path,
                    'addresses': ['127.0.0.1'], 'ca_file': str(certificate), 'credential_file': credentials['native-token'][1], 'api_version': version}
                    for kind, path, version in [('server','/v2.1','2.1'),('network','/v2.0','2.0'),('volume','/v3/project-a','3.0')]],
                'freshness_seconds': 300, 'requests_per_minute': 600, 'concurrency': 2,
                'tenant_concurrency': 1, 'max_pages': 100, 'expires_at': time.time()+3600,
                'coverage_reference': 'independent-synthetic-fixture-only',
            }
            second = copy.deepcopy(policy)
            second['policy_id'], second['epoch'] = str(uuid.uuid4()), str(uuid.uuid4())
            policies = private/'policies.json'
            policies.write_text(json.dumps({'version': 1, 'policies': [policy, second]}))
            policies.chmod(0o600)
            control = private/'worker-control.json'
            control.write_text(json.dumps({'base_url': 'https://127.0.0.1:8444', 'addresses': ['127.0.0.1'], 'ca_file': str(certificate), 'credential_file': credentials['worker-inventory'][1]}))
            envs['inventory']['INVENTORY_SITE_POLICIES_FILE'] = str(policies)
            worker_env = os.environ | {'INVENTORY_SITE_POLICIES_FILE': str(policies), 'INVENTORY_CONTROL_PLANE_FILE': str(control)}
            native = NativePeer(certificate, key, credentials['native-token'][0])
            proxies.append(native)
            for name in directories:
                start(name)
            context = ssl.create_default_context(cafile=str(certificate))

            def wire(base, path, method='GET', body=None, headers=None):
                req = urllib.request.Request(base+path, data=None if body is None else json.dumps(body).encode(), method=method,
                    headers={'Accept': 'application/json', 'Content-Type': 'application/json', **(headers or {})})
                try:
                    response = urllib.request.urlopen(req, context=context, timeout=15)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    payload = response.read(310001)
                    if len(payload) > 310000:
                        raise RuntimeError('unbounded_wire_response')
                    return response.status, json.loads(payload), response.headers, len(payload)

            def gov(path, body, token=None, expected=201):
                status, value, _, _ = wire('https://127.0.0.1:8442', path, 'POST', body, {'Authorization': 'Bearer '+credentials['console-governance'][0], 'X-Console-Session': token or fixture['admin_token'], 'Idempotency-Key': str(uuid.uuid4())})
                if status != expected:
                    raise RuntimeError('governance_wire_'+path+'_'+str(status))
                return value

            tenant = fixture['tenant']

            def inventory(operation, body=None, params=None, key=None, revision=None, expected=None, token=None, selected_tenant=None):
                op = OPERATIONS[operation]
                parameters = {'tenant': selected_tenant or tenant, 'site': site, **(params or {})}
                grant = gov('/v1/tenants/'+parameters['tenant']+'/actor-delegations', {
                    'audience': 'inventory', 'action': op['action'], 'scope': {
                        'site_id': site if '{site}' in op['path'] else None, 'environment': None, 'resource_id': None}}, token=token)
                private_values.append(grant['delegation_token'])
                headers = {'Authorization': 'Bearer '+credentials['console-inventory'][0], 'X-Actor-Delegation': grant['delegation_token']}
                if op['method'] != 'GET':
                    headers['Idempotency-Key'] = key or str(uuid.uuid4())
                if revision is not None:
                    headers['If-Match'] = '"'+str(revision)+'"'
                status, value, returned, size = wire('https://127.0.0.1:8444', op['path'].format(**parameters), op['method'], body, headers)
                wanted = op['status'] if expected is None else expected
                if status != wanted:
                    raise RuntimeError(operation+'_expected_'+str(wanted)+'_got_'+str(status)+':'+json.dumps(value))
                OAS31Validator({'$ref': '#/components/schemas/'+(op['schema'] if status < 400 else 'Error'), 'components': api['components']}).validate(value)
                check(operation+'-bounded-no-store', size < 310000 and 'no-store' in returned.get('Cache-Control', ''))
                return value

            policies_view = inventory('listPolicies')
            check('independent-approved-policies-visible', len(policies_view['items']) == 2)
            command_key = str(uuid.uuid4())
            enrolled = inventory('enrollEndpoint', {'policy_id': policy['policy_id'], 'label': 'P05 observed endpoint'}, key=command_key)
            endpoint = enrolled['endpoint_id']
            check('idempotent-enrollment-one-endpoint', inventory('enrollEndpoint', {'policy_id': policy['policy_id'], 'label': 'P05 observed endpoint'}, key=command_key) == enrolled and sql('SELECT count(*) FROM inventory.endpoints;', 'inventory') == '1')
            inventory('enrollEndpoint', {'policy_id': policy['policy_id'], 'label': 'Changed'}, key=command_key, expected=409)
            inventory('listSites')
            inventory('siteHealth')

            def scan():
                return inventory('requestDiscovery', {}, {'endpoint': endpoint})['discovery_id']

            def collect_page(label):
                time.sleep(.11)
                run([str(root/'workers/inventory/.venv/bin/inventory-worker-collect'), '--pages', '1'], env=worker_env, label=label)

            def finish(job, label):
                for index in range(15):
                    if sql("SELECT status FROM inventory.jobs WHERE id='"+job+"';", 'inventory') in {'complete', 'partial'}:
                        break
                    collect_page(label+'-'+str(index))
                else:
                    raise RuntimeError('collection_did_not_finish')

            first = scan()
            collect_page('first-page')
            check('partial-pages-not-published', inventory('listResources', params={'generation': first})['items'] == [])
            stop('inventory')
            start('inventory')
            finish(first, 'resumed-page')
            resources = inventory('listResources', params={'generation': first})
            check('complete-generation-with-provider-lowered-page-limit', resources['completion'] == 'complete' and len(resources['items']) == 4)
            check('observations-have-provenance-expiry-no-reservations', all(r['expires_at'] > r['collected_at'] and r['ownership'] == 'observation_only' and r['reserved'] is False for r in resources['items']))
            stable = {r['observation']['native_id']: r['resource_id'] for r in resources['items']}
            # Actual service/worker process restart cannot discard pagination or observations.
            check('restart-retained-pages', int(sql("SELECT page_count FROM inventory.jobs WHERE id='"+first+"';", 'inventory')) == 7)
            inventory('listResources', params={'generation': first}, token=fixture['foreign_token'], selected_tenant=fixture['foreign_tenant'], expected=404)
            inventory('renewEndpoint', {}, {'endpoint': endpoint}, revision=99, expected=412)
            native.mode = 'permission_gap'
            partial = scan()
            finish(partial, 'partial-page')
            incomplete = inventory('listResources', params={'generation': partial})
            check('permission-gap-visible-not-empty-success', incomplete['completion'] == 'partial' and incomplete['reason'] == 'permission_denied' and incomplete['items'] == [])
            check('partial-retains-previous-generation-without-tombstone', inventory('listEndpoints')['items'][0]['generation_id'] == first and sql('SELECT count(*) FROM inventory.resources WHERE tombstone;', 'inventory') == '0')
            native.mode = 'complete'
            current = scan()
            finish(current, 'fresh-page')
            newest = inventory('listResources', params={'generation': current})
            check('stable-native-identities-across-generations', stable == {r['observation']['native_id']: r['resource_id'] for r in newest['items']})
            historical = inventory('listResources', params={'generation': first})
            check('historical-generation-held', all('historical_generation' in r['holds'] for r in historical['items']))
            inventory('listDiscoveries', params={'endpoint': endpoint})
            check('independent-native-state-unchanged', native.unchanged() and all(r['method'] == 'GET' and '169.254' not in r['path'] for r in native.requests))
            (out/'native-observer.json').write_text(json.dumps({'synthetic_only': True, 'before_sha256': native.before, 'unchanged': native.unchanged(), 'requests': native.requests}, indent=2)+'\n')

            campaign(locals(), extension)
            for name in directories:
                log = (private/(name+'.log')).read_text()
                (out/(name+'-http.log')).write_text(redact(log))
                check(name+'-logs-exclude-credentials', all(value not in log for value in private_values))
            report['result'] = 'PASS'
    except Exception as error:
        report['result'] = 'FAIL'
        report['error'] = redact(str(error))
    finally:
        for name in list(processes):
            stop(name)
        for proxy in proxies:
            proxy.close()
        for handle in handles:
            handle.close()
        if broker:
            broker.close()
        report['source_unchanged'] = all(hashlib.sha256((root/n).read_bytes()).hexdigest() == value for n, value in report['source_sha256'].items())
        if not report['source_unchanged']:
            report['result'] = 'FAIL'
        report['artifact_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
        (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: report.get(k) for k in ['result', 'error']}))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
