#!/usr/bin/env python3
"""Verify P02 identity, tenancy and approval slices in disposable CI.

Passwords/terminal output stay in memory/private scratch; only redacted observations
and source bindings enter retained evidence. This never targets an operated system.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import secrets
import select
import signal
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

from synthetic_oidc import SyntheticOidc
from notification_fixture import NotificationBroker, NotificationPump
from recovery_fixture import IdentityRecovery
from recovery_ceremony import qualify_ceremony

from openapi_schema_validator import OAS31Validator
from openapi_spec_validator import validate_spec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('P02_TEST_POSTGRES') != '1':
        parser.error('Requires the disposable P02 GitHub Actions PostgreSQL service.')
    browser = os.environ.get('P02_BROWSER_ENGINE', 'chromium')
    if browser not in {'chromium', 'firefox', 'webkit'}:
        parser.error('Unsupported P02 browser engine.')
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'result': 'RUNNING', 'scope': 'P02 identity, tenancy and plan-bound approval increments',
              'source_sha': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
              'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'], 'browser_engine': browser, 'observed_at': dt.datetime.now(dt.UTC).isoformat(),
              'checks': [], 'source_sha256': {}, 'limitations': ['Synthetic HTTPS OIDC peer; no operated-provider interoperability or DNS rotation qualification', 'Synthetic immutable plan authority; no real planning producer or native admission', 'No operated deployment or G01/G02 acceptance', 'Verified PostgreSQL TLS; loopback HTTP between applications; production ingress/workload TLS topology remains unqualified']}
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    for name in tracked:
        if name and name.startswith(('services/governance/', 'apps/console/', 'scripts/p02/', 'scripts/recovery/', '.github/workflows/p02-identity', 'contracts/openapi/governance-', 'contracts/openapi/planning-', 'contracts/schemas/events/governance-', 'contracts/schemas/events/identity-', 'contracts/schemas/events/support-', 'contracts/asyncapi/identity.', 'contracts/asyncapi/support.', 'deploy/dependencies/stateful/')):
            report['source_sha256'][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    private_values = [os.environ['P02_TEST_PASSWORD']]
    processes: list[subprocess.Popen] = []
    handles = []
    provider = None
    broker = None
    pump = None

    def redact(value: str) -> str:
        for secret in private_values + (provider.private_values if provider is not None else []):
            value = value.replace(secret, '[REDACTED]')
        return value

    def check(name: str, condition: bool) -> None:
        report['checks'].append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise RuntimeError(name)

    def run(command: list[str], *, cwd: Path = root, env: dict | None = None, data: str | None = None, expected: int = 0, label: str | None = None, timeout: int = 120) -> str:
        try:
            completed = subprocess.run(command, cwd=cwd, env=env, input=data, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            if label:
                partial = error.stdout or b''
                if isinstance(partial, bytes):
                    partial = partial.decode('utf-8', errors='replace')
                (output / f'{label}.log').write_text(redact(partial))
            raise
        if label:
            (output / f'{label}.log').write_text(redact(completed.stdout))
        if completed.returncode != expected:
            raise RuntimeError(f'{label or command[0]} failed with exit {completed.returncode}: {redact(completed.stdout[-3000:])}')
        return completed.stdout

    pg_env = os.environ | {'PGHOST': '127.0.0.1', 'PGPORT': '5432', 'PGUSER': 'postgres', 'PGPASSWORD': os.environ['P02_TEST_PASSWORD']}

    def sql(statement: str, database: str = 'p02_identity_test', user: str = 'postgres', password: str | None = None, expected: int = 0) -> str:
        environment = pg_env | {'PGUSER': user, 'PGPASSWORD': password or pg_env['PGPASSWORD']}
        return run(['psql', '-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-d', database], env=environment, data=statement, expected=expected)

    def terminal(environment: dict, directory: Path) -> tuple[subprocess.Popen, int]:
        master, slave = pty.openpty()
        process = subprocess.Popen(['php', 'artisan', 'identity:bootstrap', '--console-url=http://127.0.0.1:8031'], cwd=directory, env=environment, stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        os.close(slave)
        return process, master

    def receive(pair: tuple[subprocess.Popen, int], expected: int = 0) -> str:
        process, master = pair
        result = b''
        deadline = time.monotonic() + 20
        try:
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 8192)
                    except OSError:
                        break
                    if not chunk:
                        break
                    result += chunk
                elif process.poll() is not None:
                    break
            check('interactive-bootstrap-command-exit-' + str(expected), process.wait(timeout=2) == expected)
        finally:
            os.close(master)
            if process.poll() is None:
                process.kill()
                process.wait()
        return result.decode()

    try:
        api = json.loads((root / 'contracts/openapi/governance-local-identity-v1.json').read_text())
        validate_spec(api)
        check('openapi-specification-valid', True)
        for contract in sorted((root / 'contracts/openapi').glob('governance-*.json')):
            validate_spec(json.loads(contract.read_text()))
            check('openapi-valid-' + contract.stem, True)
        run(['python', '-m', 'unittest', 'discover', '-s', 'scripts/recovery', '-p', 'test_*.py', '-v'], label='independent-custody-tests')
        check('independent-custody-positive-negative-and-crash-cases', True)
        report['php'] = run(['php', '-r', 'echo PHP_VERSION;']).strip()
        report['postgres'] = sql('SHOW server_version;').strip()
        report['node'] = run(['node', '--version']).strip()
        check('exact-php-runtime', report['php'] == '8.5.11')
        run(['php', 'vendor/bin/pest', 'tests/Feature/LocalIdentityTest.php', 'tests/Feature/IdentityAdmissionTest.php', 'tests/Feature/IdentityRecoveryTest.php', 'tests/Feature/OidcIdentityTest.php', 'tests/Feature/TenancyTest.php', 'tests/Feature/DirectoryTest.php', 'tests/Feature/ApprovalTest.php', 'tests/Feature/GovernanceOutboxTest.php', 'tests/Feature/IdentityOutboxTest.php', 'tests/Feature/ActorDelegationTest.php', 'tests/Feature/SupportTrustTest.php', 'tests/Feature/SupportAccessTest.php', 'tests/Feature/SupportContractTest.php', 'tests/Feature/SupportOutboxTest.php', 'tests/Feature/SupportConcurrencyTest.php', '--fail-on-warning', '--fail-on-risky', '--fail-on-empty-test-suite', '--colors=never'], cwd=root / 'services/governance', env=os.environ.copy(), label='postgres-features', timeout=300)
        check('postgres-feature-suite', True)

        with tempfile.TemporaryDirectory(prefix='p02-identity-') as private:
            private_path = Path(private)
            history = IdentityRecovery(os.environ['P02_POSTGRES_CONTAINER'], private_path, run, sql, check)
            run(['php', 'vendor/bin/pest', 'tests/Feature/ApprovalTest.php', '--filter=retains nonempty terminal decision history',
                 '--fail-on-warning', '--fail-on-risky', '--fail-on-empty-test-suite', '--colors=never'],
                cwd=root / 'services/governance', env=os.environ.copy(), label='approval-history-producer')
            approval_before = history.fingerprint('p02_identity_test')
            check('approval-history-persists-after-producer-process-exit', approval_before['approvals']['rows'] == 2
                  and int(sql("SELECT count(*) FROM app.governance_audit WHERE event LIKE 'governance.approval.%';", 'p02_identity_test').strip()) == 5)
            approval_archive = history.capture('p02_identity_test', 'approval-history')
            history.restore('p02_identity_test', 'approval-history')
            check('approval-history-complete-database-restore', history.fingerprint('p02_identity_test') == approval_before)
            report['approval_history_recovery'] = {'source': 'real approval owner actions with synthetic immutable plan and OIDC fixtures',
                'snapshot_sha256': approval_archive, 'table_fingerprints': approval_before,
                'decision_states': ['rejected', 'revoked'], 'approval_events': 5,
                'limits': ['No native effect or real P05 plan producer', 'Restored authority is not resumed']}
            check('packaged-support-openapi-contract', (root / 'contracts/openapi/governance-support-v1.json').read_bytes() == (root / 'services/governance/resources/contracts/governance-support-v1.json').read_bytes())
            run(['php', 'vendor/bin/pest', 'tests/Feature/SupportAccessTest.php', '--filter=retains nonempty terminal support history',
                 '--fail-on-warning', '--fail-on-risky', '--fail-on-empty-test-suite', '--colors=never'],
                cwd=root / 'services/governance', env=os.environ.copy(), label='support-history-producer')
            support_before = history.fingerprint('p02_identity_test')
            check('support-history-persists-after-producer-process-exit', support_before['support_requests']['rows'] == 1
                  and support_before['support_approvals']['rows'] == 2 and support_before['support_reviews']['rows'] == 1
                  and support_before['support_audit']['rows'] == 10 and support_before['support_outbox']['rows'] == 10)
            support_archive = history.capture('p02_identity_test', 'support-history')
            history.restore('p02_identity_test', 'support-history')
            check('support-history-complete-database-restore', history.fingerprint('p02_identity_test') == support_before)
            check('restored-support-request-stays-terminal', sql("SELECT state || ':' || admission_count FROM app.support_requests;", 'p02_identity_test').strip() == 'revoked:1')
            report['support_history_recovery'] = {'source': 'real support owner actions with synthetic OIDC fixture',
                'snapshot_sha256': support_archive, 'table_fingerprints': support_before,
                'decision_states': ['revoked'], 'approvals': 2, 'admissions': 1, 'reviews': 1, 'audit_events': 10,
                'limits': ['No native effect or Console support UI', 'Restored authority is not resumed', 'Actual audit custodian remains an operating input']}
            broker = NotificationBroker(root, private_path, run, private_values)
            broker.start()
            report['notification_broker_image'] = broker.image
            check('console-packaged-governance-contract', (root / 'contracts/schemas/events/governance-change-v1.json').read_bytes() == (root / 'apps/console/resources/contracts/governance-change-v1.json').read_bytes())
            check('console-packaged-identity-contract', (root / 'contracts/schemas/events/identity-change-v1.json').read_bytes() == (root / 'apps/console/resources/contracts/identity-change-v1.json').read_bytes())
            run(['php', 'vendor/bin/pest', 'tests/Feature/NotificationInboxTest.php', 'tests/Feature/NotificationContractTest.php',
                 'tests/Feature/NotificationAccessTest.php', 'tests/Feature/InstallationNotificationTest.php', 'tests/Feature/DirectoryTest.php', 'tests/Feature/NotificationBrokerTest.php', '--fail-on-warning', '--fail-on-risky', '--colors=never'],
                cwd=root / 'apps/console', env=os.environ | broker.environment, label='console-notification-features')
            check('console-postgres-and-tls-notification-features', True)
            provider = SyntheticOidc(private_path)
            provider.start()
            private_values.append(provider.client_secret)
            # Exercise the existing Console's verified-TLS and mounted-secret contract.
            certificate, key_file = private_path / 'postgres.crt', private_path / 'postgres.key'
            run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key_file), '-out', str(certificate), '-days', '1', '-subj', '/CN=p02-disposable-postgres', '-addext', 'subjectAltName=IP:127.0.0.1,DNS:localhost'])
            container = os.environ['P02_POSTGRES_CONTAINER']
            check('isolated-postgres-container-id', re.fullmatch(r'[0-9a-f]{64}', container) is not None)
            run(['docker', 'exec', container, 'mkdir', '-p', '/tmp/p02-tls'])
            for path in [certificate, key_file]:
                run(['docker', 'cp', str(path), container + ':/tmp/p02-tls/' + path.name])
            run(['docker', 'exec', container, 'chown', '-R', 'postgres:postgres', '/tmp/p02-tls'])
            run(['docker', 'exec', container, 'chmod', '0600', '/tmp/p02-tls/postgres.key'])
            sql("ALTER SYSTEM SET ssl_cert_file='/tmp/p02-tls/postgres.crt'; ALTER SYSTEM SET ssl_key_file='/tmp/p02-tls/postgres.key'; ALTER SYSTEM SET ssl='on'; SELECT pg_reload_conf();")
            pg_env.update(PGSSLMODE='verify-full', PGSSLROOTCERT=str(certificate))
            deadline = time.monotonic() + 5
            while True:
                try:
                    check('postgres-verified-tls', sql('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid();').strip() == 't')
                    break
                except RuntimeError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            credential = secrets.token_hex(32)
            private_values.append(credential)
            credential_file = private_path / 'console-identity'
            credential_file.write_text(credential)
            credential_file.chmod(0o600)
            admission_file = private_path / 'identity-admission.json'
            admission = {'version': 1, 'installation_id': '550e8400-e29b-41d4-a716-446655440099', 'epoch': secrets.token_hex(32), 'state': 'active', 'bootstrap_allowed': True}
            admission_file.write_text(json.dumps(admission))
            admission_file.chmod(0o600)
            environments = {}
            recovery_owner_environment = {}
            for name, directory in [('governance', 'services/governance'), ('console', 'apps/console')]:
                runtime_password, migration_password = secrets.token_hex(32), secrets.token_hex(32)
                private_values.extend([runtime_password, migration_password])
                password_file = private_path / (name + '-db-password')
                password_file.write_text(runtime_password)
                password_file.chmod(0o600)
                sql(f"CREATE ROLE {name}_owner NOLOGIN; CREATE ROLE {name}_runtime LOGIN NOINHERIT PASSWORD '{runtime_password}'; CREATE ROLE {name}_migrator LOGIN NOINHERIT PASSWORD '{migration_password}'; GRANT {name}_owner TO {name}_migrator WITH INHERIT FALSE, SET TRUE; CREATE DATABASE {name} OWNER {name}_owner;")
                sql(f'REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {name}_runtime, {name}_migrator;', name)
                sql(f'REVOKE ALL ON SCHEMA public FROM PUBLIC; CREATE SCHEMA app AUTHORIZATION {name}_owner; GRANT USAGE ON SCHEMA app TO {name}_runtime;', name)
                sql(f'ALTER DEFAULT PRIVILEGES FOR ROLE {name}_owner IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {name}_runtime;', name)
                migration = root / directory / 'database/migrations' / ('001_identity.sql' if name == 'governance' else '001_shared_state.sql')
                for owned_migration in sorted(migration.parent.glob('*.sql')):
                    sql(owned_migration.read_text(), name, f'{name}_migrator', migration_password)
                key = 'base64:' + base64.b64encode(secrets.token_bytes(32)).decode()
                private_values.append(key)
                environments[name] = os.environ | broker.environment | {'APP_ENV': 'p02-verification', 'APP_DEBUG': 'false', 'APP_KEY': key,
                    'GOVERNANCE_IDENTITY_ADMISSION_FILE': str(admission_file),
                    'APP_URL': f'http://127.0.0.1:{8032 if name == "governance" else 8031}',
                    'DB_HOST': '127.0.0.1', 'DB_PORT': '5432', 'DB_DATABASE': name, 'DB_USERNAME': f'{name}_runtime',
                    'DB_PASSWORD': runtime_password, 'DB_PASSWORD_FILE': str(password_file), 'DB_SSLMODE': 'verify-full', 'DB_SSLROOTCERT': str(certificate), 'CONSOLE_CREDENTIAL_FILE': str(credential_file),
                    'GOVERNANCE_URL': 'http://127.0.0.1:8032', 'SESSION_DRIVER': 'database', 'CACHE_STORE': 'database', 'SESSION_SECURE_COOKIE': 'false'}
                if name == 'governance':
                    recovery_owner_environment = environments[name] | {'DB_USERNAME': 'governance_migrator', 'DB_PASSWORD': migration_password}
            for label, statement in [('inbox-update', "UPDATE app.notification_inbox SET event_type='forged';"),
                                     ('inbox-delete', 'DELETE FROM app.notification_inbox;'),
                                     ('quarantine-delete', 'DELETE FROM app.notification_quarantine;'),
                                     ('quarantine-update', "UPDATE app.notification_quarantine SET reason='forged';")]:
                denial = sql(statement, 'console', 'console_runtime', environments['console']['DB_PASSWORD'], expected=3)
                check('console-runtime-denied-' + label, 'permission denied' in denial)
            gov = root / 'services/governance'
            # A redirected invocation must fail before changing the provisioned sentinel.
            run(['php', 'artisan', 'identity:bootstrap', '--console-url=http://127.0.0.1:8031'], cwd=gov, env=environments['governance'], expected=1, label='noninteractive-denial')
            check('noninteractive-does-not-initialize', sql('SELECT state FROM app.bootstrap_administrator;', 'governance').strip() == 'uninitialized')
            contenders = [terminal(environments['governance'], gov), terminal(environments['governance'], gov)]
            displays = [receive(contender) for contender in contenders]
            passwords = re.findall(r'Temporary password: ([0-9a-f]{48})', '\n'.join(displays))
            private_values.extend(passwords)
            check('concurrent-deployment-displays-exactly-one-credential', len(passwords) == 1)
            temporary = passwords[0]
            check('one-bootstrap-event-and-outbox', sql("SELECT (SELECT count(*) FROM app.identity_audit WHERE event='identity.bootstrap.created') || ':' || (SELECT count(*) FROM app.identity_outbox);", 'governance').strip() == '1:1')
            before = sql('SELECT password_hash FROM app.bootstrap_administrator;', 'governance').strip()
            for migration in sorted((gov / 'database/migrations').glob('*.sql')):
                sql(migration.read_text(), 'governance')
            check('migration-replay-preserves-credential', sql('SELECT password_hash FROM app.bootstrap_administrator;', 'governance').strip() == before)
            replay = receive(terminal(environments['governance'], gov))
            check('fresh-process-retry-does-not-redisplay', 'Temporary password:' not in replay and 'already complete' in replay)

            runtime_password = environments['governance']['DB_PASSWORD']
            for label, statement in [('sentinel-delete', 'DELETE FROM app.bootstrap_administrator;'), ('audit-delete', 'DELETE FROM app.identity_audit;'), ('audit-update', "UPDATE app.identity_audit SET event='forged';"), ('schema-create', 'CREATE TABLE app.forbidden (id int);'), ('governance-audit-update', "UPDATE app.governance_audit SET event='forged';"), ('governance-audit-delete', 'DELETE FROM app.governance_audit;'), ('approval-binding-update', "UPDATE app.approvals SET plan_digest='forged';"), ('receipt-delete', 'DELETE FROM app.governance_commands;'), ('outbox-payload-update', "UPDATE app.governance_outbox SET payload_json='forged';"), ('outbox-delete', 'DELETE FROM app.governance_outbox;'), ('identity-outbox-event-update', "UPDATE app.identity_outbox SET event='forged';"), ('identity-outbox-delete', 'DELETE FROM app.identity_outbox;'), ('support-binding-update', "UPDATE app.support_requests SET binding_json='forged';"), ('support-request-delete', 'DELETE FROM app.support_requests;'), ('support-role-scope-update', "UPDATE app.support_security_grants SET site_id='forged';"), ('support-approval-update', "UPDATE app.support_approvals SET authority_sha256='forged';"), ('support-approval-delete', 'DELETE FROM app.support_approvals;'), ('support-review-update', "UPDATE app.support_reviews SET outcome='incident';"), ('support-review-delete', 'DELETE FROM app.support_reviews;'), ('support-audit-update', "UPDATE app.support_audit SET event='forged';"), ('support-audit-delete', 'DELETE FROM app.support_audit;'), ('support-outbox-update', "UPDATE app.support_outbox SET payload_json='forged';"), ('support-outbox-delete', 'DELETE FROM app.support_outbox;')]:
                denial = sql(statement, 'governance', 'governance_runtime', runtime_password, expected=3)
                check('runtime-denied-' + label, 'permission denied' in denial)
            replacement = secrets.token_urlsafe(32)
            private_values.append(replacement)
            fixture = private_path / 'bootstrap.json'
            fixture.write_text(json.dumps({'temporary': temporary, 'replacement': replacement, 'provider': provider.fixture()}))
            fixture.chmod(0o600)
            def stop_applications():
                for process in processes:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        process.wait(timeout=10)
                processes.clear()

            def start_applications():
                for name, directory in [('governance', gov), ('console', root / 'apps/console')]:
                    port = 8032 if name == 'governance' else 8031
                    handle = (private_path / f'{name}.log').open('ab')
                    handles.append(handle)
                    router = directory / 'vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php'
                    process = subprocess.Popen(['php', '-d', 'curl.cainfo=' + str(provider.certificate), '-S', f'127.0.0.1:{port}', str(router)], cwd=directory / 'public', env=environments[name], stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
                    processes.append(process)
                    deadline = time.monotonic() + 20
                    while True:
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health/live', timeout=1) as response:
                                check(name + '-http-started', response.status == 200)
                            break
                        except OSError:
                            if process.poll() is not None or time.monotonic() > deadline:
                                log = (private_path / f'{name}.log').read_text()
                                (output / f'{name}-http.log').write_text(redact(log))
                                raise RuntimeError(name + ' did not start: ' + redact(log[-2000:]))
                            time.sleep(0.1)
            start_applications()
            def wire(path: str, schema: str | dict, expected: int = 200, body: dict | None = None, token: str = '', workload: str | None = None) -> dict:
                request = urllib.request.Request('http://127.0.0.1:8032' + path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers={'Authorization': 'Bearer ' + (workload if workload is not None else credential), 'X-Console-Session': token, 'Content-Type': 'application/json', 'Accept': 'application/json'})
                try:
                    response = urllib.request.urlopen(request, timeout=5)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    value = json.loads(response.read())
                    check('wire-' + path + '-' + str(expected), response.status == expected)
                    validator = {'$ref': '#/components/schemas/' + schema, 'components': api['components']} if isinstance(schema, str) else schema
                    OAS31Validator(validator).validate(value)
                    check('wire-' + path + '-no-store', 'no-store' in response.headers.get('Cache-Control', ''))
                    return value
            initial_session = wire('/identity/local-sessions', 'Session', body={'username': 'admin', 'password': temporary})['session_token']
            private_values.append(initial_session)
            wire('/identity/session', 'CurrentIdentity', token=initial_session)
            wire('/identity/setup', 'Error', expected=403, token=initial_session)
            recovery = IdentityRecovery(container, private_path, run, sql, check)
            recovery.capture('governance', 'governance-before-activation')
            browser_env = os.environ | {'P02_BOOTSTRAP_FILE': str(fixture), 'CONSOLE_BASE_URL': 'http://127.0.0.1:8031'}
            pump = NotificationPump(root, environments)
            pump.thread.start()
            try:
                run(['npx', 'playwright', 'test', '--config=playwright.p02.config.ts'], cwd=root / 'apps/console', env=browser_env, label='browser')
            finally:
                for name in ['governance', 'console']:
                    (output / f'{name}-http.log').write_text(redact((private_path / f'{name}.log').read_text()))
            pump.close()
            report['notification_delivery'] = {'cycles': pump.cycles, 'counts': pump.totals, 'error': pump.error}
            check('real-owner-relay-and-console-consumer', pump.error is None and pump.totals['published'] >= 1 and pump.totals['recorded'] >= 1
                  and pump.totals['retry'] == 0 and pump.totals['quarantined'] == 0)
            check('installation-identity-delivered-to-product-consumer', int(sql('SELECT count(*) FROM app.notification_inbox WHERE tenant_id IS NULL;', 'console').strip()) > 0
                  and sql('SELECT count(*) FROM app.installation_notification_hint;', 'console').strip() == '1')
            check('console-inbox-is-not-a-domain-projection', sql('SELECT count(*) FROM app.notification_inbox;', 'console').strip() == str(pump.totals['recorded']))
            browser_report = root / 'apps/console/test-results/p02-browser.json'
            browser_result = json.loads(browser_report.read_text())
            projects = browser_result['config']['projects']
            check('requested-browser-engine-ran', len(projects) == 1 and projects[0]['name'] == browser)
            stats = browser_result['stats']
            report['browser_stats'] = stats
            (output / 'browser.json').write_text(redact(browser_report.read_text()))
            check('browser-no-skips-retries-or-failures', stats['expected'] == 2 and all(stats[key] == 0 for key in ['unexpected', 'flaky', 'skipped']))
            check('handover-retired-local-and-destroyed-password', sql("SELECT state || ':' || credential_version || ':' || (password_hash IS NULL)::text FROM app.bootstrap_administrator;", 'governance').strip() == 'retired:3:true')
            check('provider-https-pkce-exchanges', provider.counts['token'] >= 3 and provider.counts['pkce_verified'] == provider.counts['token'])
            report['synthetic_provider'] = provider.counts
            check('tenant-audit-and-outbox-stay-paired', sql('SELECT count(*) FROM app.governance_audit a FULL JOIN app.governance_outbox o USING (id) WHERE a.id IS NULL OR o.id IS NULL;', 'governance').strip() == '0')
            check('two-independent-tenants-persisted', sql('SELECT count(*) FROM app.tenants;', 'governance').strip() == '2')
            check('reader-revocation-persisted', sql("SELECT count(*) FROM app.tenant_memberships WHERE role='reader' AND state='revoked';", 'governance').strip() == '1')
            wire('/identity/session', 'Error', expected=401, token=initial_session)
            check('audit-and-outbox-stay-paired', sql('SELECT count(*) FROM app.identity_audit a FULL JOIN app.identity_outbox o USING (id) WHERE a.id IS NULL OR o.id IS NULL;', 'governance').strip() == '0')
            report['recovery'] = recovery.qualify(stop_applications, start_applications, wire, admission, admission_file,
                initial_session, temporary, lambda expected=0: receive(terminal(environments['governance'], gov), expected))
            report['independent_recovery_ceremony'] = qualify_ceremony(root, private_path, run, sql, check, recovery, stop_applications, start_applications,
                environments, recovery_owner_environment, provider, wire, private_values, initial_session)
            for name in ['governance', 'console']:
                log = (private_path / f'{name}.log').read_text()
                check(name + '-logs-exclude-credentials', all(value not in log for value in private_values + provider.private_values))
        report['result'] = 'PASS'
    except Exception as error:
        report['result'] = 'FAIL'
        report['failure'] = redact(str(error))
    finally:
        if pump is not None:
            pump.close()
        if broker is not None:
            broker.close()
        if provider is not None:
            provider.close()
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
        for handle in handles:
            handle.close()
        report['completed_at'] = dt.datetime.now(dt.UTC).isoformat()
        report['artifact_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'result': report['result'], 'checks': len(report['checks']), 'failure': report.get('failure')}))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
