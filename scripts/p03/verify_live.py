#!/usr/bin/env python3
"""P03 disposable PostgreSQL, TLS API, confirmed broker and compiled browser campaign."""
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
from generated_operations import OPERATIONS
from live_fixture import CatalogueBroker, TlsProxy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('P03_TEST_POSTGRES') != '1':
        parser.error('Requires the disposable P03 GitHub Actions service.')
    engine = os.environ.get('P03_BROWSER_ENGINE', 'chromium')
    if engine not in ['chromium', 'firefox', 'webkit']:
        parser.error('Unsupported browser.')
    root = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'result': 'RUNNING', 'source_revision': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
        'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'], 'browser_engine': engine, 'observed_at': datetime.datetime.now(datetime.UTC).isoformat(),
        'checks': [], 'commands': [], 'limitations': ['Synthetic OIDC transport used only by the separate principal bootstrap process; live requests use real Governance current authority.',
            'Independent broker observer, not a Planning product consumer; Planning is P05.',
            'TLS application peers terminate at disposable loopback forwarding proxies; no operated ingress qualification.',
            'Automated browser checks do not establish representative operator, screen-reader or independent G03 receiving acceptance.']}
    paths = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
    report['source_sha256'] = {n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in paths if n.startswith(('services/catalogue/', 'services/governance/', 'apps/console/', 'contracts/', 'scripts/p03/', '.github/workflows/p03'))}
    private_values = [os.environ['P03_ADMIN_PASSWORD']]
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
        with tempfile.TemporaryDirectory(prefix='p03-live-') as directory:
            try:
                yield directory
            finally:
                for name in ['governance', 'catalogue', 'console']:
                    log = Path(directory)/(name+'.log')
                    if log.exists():
                        (out/(name+'-http.log')).write_text(redact(log.read_text()))
                browser_file = root/'apps/console/test-results/p03-browser.json'
                if browser_file.exists():
                    (out/'browser.json').write_text(redact(browser_file.read_text()))

    try:
        api = json.loads((root/'contracts/openapi/catalogue-v1.0.1.json').read_text())
        validate_spec(api)
        check('independent-openapi-specification-validation', True)
        run(['python', 'scripts/p03/generate_clients.py', '--check'], label='generated-clients')
        with private_directory() as directory:
            private = Path(directory)
            certificate, key = private/'services.crt', private/'services.key'
            run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key), '-out', str(certificate), '-days', '1', '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost'])
            container = os.environ['P03_POSTGRES_CONTAINER']
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
            for name in ['console-governance', 'catalogue-governance', 'console-catalogue']:
                value = secrets.token_hex(32)
                private_values.append(value)
                file = private/name
                file.write_text(value)
                file.chmod(0o600)
                credentials[name] = (value, str(file))
            admission = private/'identity-admission.json'
            admission.write_text(json.dumps({'version': 1, 'installation_id': str(uuid.uuid4()), 'epoch': secrets.token_hex(32), 'state': 'active', 'bootstrap_allowed': True}))
            admission.chmod(0o600)
            directories = {'governance': 'services/governance', 'catalogue': 'services/catalogue', 'console': 'apps/console'}
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
                if name != 'catalogue':
                    sql(f'ALTER DEFAULT PRIVILEGES FOR ROLE {name}_owner IN SCHEMA app GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO {name}_runtime;', name)
                for migration in sorted((root/relative/'database/migrations').glob('*.sql')):
                    sql(migration.read_text(), name, name+'_migrator', migrator)
                app_key = 'base64:'+base64.b64encode(secrets.token_bytes(32)).decode()
                private_values.append(app_key)
                envs[name] = os.environ | {'APP_ENV': 'p03-verification', 'APP_DEBUG': 'false', 'APP_KEY': app_key,
                    'DB_HOST': '127.0.0.1', 'DB_PORT': '5432', 'DB_DATABASE': name, 'DB_USERNAME': name+'_runtime', 'DB_PASSWORD': password,
                    'DB_PASSWORD_FILE': str(password_file), 'DB_SSLMODE': 'verify-full', 'DB_SSLROOTCERT': str(certificate),
                    'GOVERNANCE_URL': 'https://127.0.0.1:8442', 'GOVERNANCE_CA_FILE': str(certificate), 'GOVERNANCE_CREDENTIAL_FILE': credentials['catalogue-governance'][1],
                    'CONSOLE_CREDENTIAL_FILE': credentials['console-governance'][1], 'CATALOGUE_GOVERNANCE_CREDENTIAL_FILE': credentials['catalogue-governance'][1],
                    'CONSOLE_CATALOGUE_CREDENTIAL_FILE': credentials['console-catalogue'][1], 'CATALOGUE_CONSOLE_CREDENTIAL_FILE': credentials['console-catalogue'][1],
                    'CATALOGUE_URL': 'https://127.0.0.1:8443', 'CATALOGUE_CA_FILE': str(certificate), 'GOVERNANCE_IDENTITY_ADMISSION_FILE': str(admission),
                    'SESSION_DRIVER': 'database', 'CACHE_STORE': 'database', 'SESSION_SECURE_COOKIE': 'false', 'APP_URL': 'http://127.0.0.1:8031', 'PHP_CLI_SERVER_WORKERS': '4'}
            fixture_file = private/'browser.json'
            run(['php', 'scripts/p03/seed_governance.php', str(fixture_file)], env=envs['governance'], label='seed-principals')
            fixture = json.loads(fixture_file.read_text())
            private_values += [fixture['admin_token'], fixture['author_token'], fixture['foreign_token']]
            run(['php', 'scripts/p03/seed_console.php', str(fixture_file)], env=envs['console'], label='seed-browser-sessions')
            fixture = json.loads(fixture_file.read_text())
            private_values += [fixture['admin_cookie']['value'], fixture['author_cookie']['value']]
            fault_file = private/'lose-next-response.json'
            for port, upstream, fault in [(8442, 8032, None), (8443, 8033, fault_file)]:
                proxies.append(TlsProxy(port, upstream, certificate, key, fault))

            def start(name):
                port = {'governance': 8032, 'catalogue': 8033, 'console': 8031}[name]
                directory = root/directories[name]
                handle = (private/(name+'.log')).open('ab')
                handles.append(handle)
                router = directory/'vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php'
                processes[name] = subprocess.Popen(['php', '-S', '127.0.0.1:'+str(port), str(router)], cwd=directory/'public', env=envs[name], stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
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

            def delegation(action, resource=None, environment=None, token=None, selected_tenant=None):
                value = gov('/v1/tenants/'+(selected_tenant or tenant)+'/actor-delegations', {'audience': 'catalogue', 'action': action,
                    'scope': {'site_id': None, 'environment': environment, 'resource_id': resource}}, token=token or fixture['author_token'])
                private_values.append(value['delegation_token'])
                return value['delegation_token']

            def catalogue(operation, body=None, params=None, key=None, etag=None, expected=None, token=None, selected_tenant=None, cursor=None, environment=None, actor_token=None):
                op = OPERATIONS[operation]
                parameters = {'tenant': selected_tenant or tenant, **(params or {})}
                path = op['path'].format(**parameters)
                scope_environment = body.get('intent', {}).get('environment', {}).get('id') if body else environment
                actor_token = actor_token or delegation(op['action'], parameters.get('application'), scope_environment, token, parameters['tenant'])
                headers = {'Authorization': 'Bearer '+credentials['console-catalogue'][0], 'X-Actor-Delegation': actor_token}
                if op['method'] != 'GET':
                    headers['Idempotency-Key'] = key or str(uuid.uuid4())
                if etag is not None:
                    headers['If-Match'] = etag
                query = {k: v for k, v in [('cursor', cursor), ('environment', environment)] if v is not None}
                if query:
                    path += '?'+urllib.parse.urlencode(query)
                status, value, headers, size = wire('https://127.0.0.1:8443', path, op['method'], body, headers)
                wanted = op['status'] if expected is None else expected
                if status != wanted:
                    raise RuntimeError(operation+'_expected_'+str(wanted)+'_got_'+str(status)+':'+json.dumps(value))
                schema = op['schema'] if status < 400 else 'Error'
                OAS31Validator({'$ref': '#/components/schemas/'+schema, 'components': api['components']}).validate(value)
                if 'no-store' not in headers.get('Cache-Control', ''):
                    raise RuntimeError('missing_no_store')
                return value

            mapping = {'00000000-0000-4000-8000-000000000002': fixture['actor_id']}
            for suffix, operation, name, zone in [(10, 'createEnvironment', 'Production', None), (11, 'createWsd', 'Frontend WSD', None), (12, 'createWsd', 'Data WSD', None), (21, 'createSecurityDomain', 'Operations', 'OZ'), (22, 'createSecurityDomain', 'Restricted', 'RZ')]:
                body = {'name': name, 'owner_id': fixture['actor_id']}
                if operation != 'createEnvironment':
                    body['shareable'] = True
                if zone:
                    body['zone'] = zone
                ref = catalogue(operation, body, token=fixture['admin_token'])
                mapping['00000000-0000-4000-8000-'+f'{suffix:012d}'] = ref['id']
            template = (root/'contracts/fixtures/catalogue/permit-desk-v1.json').read_text()

            def fresh_intent():
                replacements = dict(mapping)
                for identity in re.findall(r'00000000-0000-4000-8000-[0-9]{12}', template):
                    replacements.setdefault(identity, str(uuid.uuid4()))
                return json.loads(re.sub(r'00000000-0000-4000-8000-[0-9]{12}', lambda m: replacements[m.group()], template))

            intent = fresh_intent()
            receipt_key = str(uuid.uuid4())
            first = catalogue('createApplication', {'name': 'Wire Permit Desk', 'intent': intent}, key=receipt_key)
            app = {'application': first['application_id']}
            check('complete-multi-wsd-domain-data-recovery-intent', catalogue('getRevision', params=app | {'revision': first['revision_id']})['intent'] == intent)
            check('same-create-command-returns-original-receipt', catalogue('createApplication', {'name': 'Wire Permit Desk', 'intent': intent}, key=receipt_key) == first)
            catalogue('createApplication', {'name': 'Changed', 'intent': intent}, key=receipt_key, expected=409)
            catalogue('publishRevision', {'intent': intent}, app, expected=428)
            invalid = copy.deepcopy(intent)
            invalid['workloads'][0]['nics'][0]['security_domain_id'] = intent['workloads'][1]['security_domain']['id']
            catalogue('publishRevision', {'intent': invalid}, app, etag=first['etag'], expected=422)
            invalid = copy.deepcopy(intent)
            invalid['dependencies'].append(invalid['dependencies'][0] | {'from': intent['workloads'][1]['id'], 'to': intent['workloads'][0]['id']})
            catalogue('publishRevision', {'intent': invalid}, app, etag=first['etag'], expected=422)
            invalid = copy.deepcopy(intent)
            invalid['workloads'][0]['wsd']['id'] = str(uuid.uuid4())
            catalogue('publishRevision', {'intent': invalid}, app, etag=first['etag'], expected=422)
            catalogue('createSecurityDomain', {'name': 'Forbidden ZIP', 'owner_id': fixture['actor_id'], 'shareable': True, 'zone': 'ZIP'}, token=fixture['admin_token'], expected=422)
            # A real second tenant delegation cannot select another tenant's application.
            catalogue('getApplication', params=app, selected_tenant=fixture['foreign_tenant'], token=fixture['foreign_token'], expected=404)
            check('wire-negative-invariants-and-tenant-boundary', True)
            with ThreadPoolExecutor(max_workers=2) as pool:
                candidates = [copy.deepcopy(intent), copy.deepcopy(intent)]
                for i, value in enumerate(candidates):
                    value['workloads'][0]['compute']['vcpus'] = 4+i
                # Accept either winner, while independently checking each response contract.
                actor = delegation('application.write', app['application'], intent['environment']['id'])
                def contend(value):
                    status, result, _, _ = wire('https://127.0.0.1:8443', OPERATIONS['publishRevision']['path'].format(tenant=tenant, **app), 'POST', {'intent': value},
                        {'Authorization': 'Bearer '+credentials['console-catalogue'][0], 'X-Actor-Delegation': actor, 'If-Match': first['etag'], 'Idempotency-Key': str(uuid.uuid4())})
                    OAS31Validator({'$ref': '#/components/schemas/'+('Receipt' if status == 201 else 'Error'), 'components': api['components']}).validate(result)
                    return status, result
                contested = list(pool.map(contend, candidates))
            check('concurrent-distinct-commands-one-winner-one-stale', sorted(s for s, _ in contested) == [201, 412])
            current = next(v for s, v in contested if s == 201)
            concurrent_key = str(uuid.uuid4())
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: catalogue('publishRevision', {'intent': intent}, app, key=concurrent_key, etag=current['etag']), [0, 1]))
            check('concurrent-same-command-one-immutable-revision', results[0] == results[1] and len(catalogue('listRevisions', params=app)['revisions']) == 3)
            stop('catalogue')
            start('catalogue')
            check('process-restart-original-receipt-and-history', catalogue('createApplication', {'name': 'Wire Permit Desk', 'intent': intent}, key=receipt_key) == first and catalogue('getRevision', params=app | {'revision': first['revision_id']})['intent'] == intent)
            second_environment = catalogue('createEnvironment', {'name': 'Staging', 'owner_id': fixture['actor_id']}, token=fixture['admin_token'])
            second_intent = copy.deepcopy(intent)
            second_intent['environment'] = {'id': second_environment['id'], 'version': 1}
            second_intent['deployment_id'] = str(uuid.uuid4())
            second_receipt = catalogue('publishRevision', {'intent': second_intent}, app, etag=results[0]['etag'])
            check('separate-deployment-history-shares-application-etag', catalogue('getRevision', params=app | {'revision': second_receipt['revision_id']})['parent_id'] is None and len(catalogue('getApplication', params=app)['deployments']) == 2)
            # Synthetic skew fixture is only list metadata, never reported as authored intent.
            sql(f"INSERT INTO app.catalogue_applications(id,tenant_id,name,version) SELECT gen_random_uuid(),'{tenant}','Synthetic skew '||i,1 FROM generate_series(1,10000) i; INSERT INTO app.catalogue_applications(id,tenant_id,name,version) SELECT gen_random_uuid(),'{fixture['foreign_tenant']}','Synthetic small '||i,1 FROM generate_series(1,1001) i; ANALYZE app.catalogue_applications;", 'catalogue')
            page = catalogue('listApplications')
            page2 = catalogue('listApplications', cursor=page['next_cursor'])
            check('large-skew-pages-bounded-disjoint', len(page['applications']) == len(page2['applications']) == 50 and not ({a['id'] for a in page['applications']} & {a['id'] for a in page2['applications']}))
            catalogue('listApplications', selected_tenant=fixture['foreign_tenant'], token=fixture['foreign_token'], cursor=page['next_cursor'], expected=422)
            plan = json.loads(sql(f"EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT id,name,version FROM app.catalogue_applications WHERE tenant_id='{tenant}' AND id>'{page['applications'][-1]['id']}' ORDER BY id LIMIT 51;", 'catalogue'))
            (out/'application-page-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
            check('actual-page-query-bounded', plan[0]['Plan']['Actual Rows'] == 51 and plan[0]['Execution Time'] < 1000)
            report['scale'] = {'large_tenant_applications': 10001, 'small_tenant_applications': 1001, 'page_size': 50, 'page_bytes': len(json.dumps(page).encode()), 'page_query_execution_ms': plan[0]['Execution Time'], 'scope': 'Synthetic metadata skew; query count is separately asserted in the PostgreSQL feature campaign.'}
            # Broker unavailable before startup: accepted application history remains readable.
            broker = CatalogueBroker(root, private, run, private_values)
            envs['catalogue'].update(broker.environment)
            run(['php', 'artisan', 'catalogue:publish-events'], cwd=root/'services/catalogue', env=envs['catalogue'], expected=1, label='broker-outage')
            check('broker-outage-retains-pending-facts', int(sql('SELECT count(*) FROM app.catalogue_outbox WHERE published_at IS NULL;', 'catalogue')) >= 10)
            broker.start()
            report['broker_image'] = broker.image
            run(['php', 'scripts/p03/broker_process.php', 'denied'], env=envs['catalogue'], label='broker-acl-denial')
            run(['php', 'scripts/p03/broker_process.php', 'uncertain'], env=envs['catalogue'], label='broker-uncertain-confirmation')
            run(['php', 'artisan', 'catalogue:publish-events'], cwd=root/'services/catalogue', env=envs['catalogue'], label='broker-replay')
            events_file = private/'events.json'
            run(['php', 'scripts/p03/broker_process.php', 'observe', str(events_file)], env=envs['catalogue'], label='broker-observer')
            events = json.loads(events_file.read_text())
            schema = json.loads((root/'contracts/schemas/events/catalogue-intent-v1.json').read_text())
            for event in events:
                Draft202012Validator(schema).validate(event['body'])
                check('broker-message-id-matches-envelope', event['message_id'] == event['body']['event_id'])
            ids = [event['message_id'] for event in events]
            check('uncertain-confirmation-replays-same-event-once', len(ids) == len(set(ids))+1 and ids[0] == ids[1])
            sequences = {}
            for event in events:
                body = event['body']
                sequences.setdefault(body['resource_id'], []).append(body['sequence'])
            check('per-resource-sequence-preserved', all(values == sorted(values) for values in sequences.values()))
            check('broker-recovery-no-pending-facts', sql('SELECT count(*) FROM app.catalogue_outbox WHERE published_at IS NULL;', 'catalogue') == '0')
            report['broker_delivery'] = {'observed_messages': len(events), 'unique_events': len(set(ids)), 'duplicate_event_ids': 1, 'resource_sequences': list(sequences.values())}
            fixture.update(intent=fresh_intent(), fault_file=str(fault_file), console_workload=credentials['console-governance'][0], governance_url='https://127.0.0.1:8442')
            fixture_file.write_text(json.dumps(fixture))
            run(['npx', 'playwright', 'test', '--config=tests/browser-p03/playwright.config.ts'], cwd=root/'apps/console', env=os.environ | {'P03_BROWSER_FIXTURE': str(fixture_file), 'CONSOLE_BASE_URL': 'http://127.0.0.1:8031'}, label='browser')
            browser_file = root/'apps/console/test-results/p03-browser.json'
            browser = json.loads(browser_file.read_text())
            (out/'browser.json').write_text(redact(browser_file.read_text()))
            report['browser_stats'] = browser['stats']
            check('browser-required-engine-no-skips-retries-or-failures', browser['config']['projects'][0]['name'] == engine and browser['stats']['expected'] == 1 and all(browser['stats'][k] == 0 for k in ['unexpected', 'flaky', 'skipped']))
            check('live-post-commit-response-loss-exercised', proxies[1].injected == 1)
            check('application-audit-outbox-atomic-pairing', sql('SELECT count(*) FROM app.catalogue_audit a FULL JOIN app.catalogue_outbox o USING(event_id) WHERE a.event_id IS NULL OR o.event_id IS NULL;', 'catalogue') == '0')
            check('browser-created-exactly-four-revisions', sql("SELECT count(*) FROM app.catalogue_revisions r JOIN app.catalogue_applications a ON a.id=r.application_id WHERE a.name='Browser Permit Desk';", 'catalogue') == '4')
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
