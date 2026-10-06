"""Execute the real custody CLI and owner-only recovery commands in disposable CI.

Synthetic custodians, keys and operating records are private fixtures, never a
claim that production people or custody infrastructure have been appointed.
"""
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import secrets
import select
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def qualify_ceremony(root, private, run, sql, check, recovery, stop, start, environments, owner_environment, provider, wire, private_values, initial_session):
    sys.path.insert(0, str(root / 'scripts/recovery'))
    import custody
    directory = private / 'recovery-ceremony'
    directory.mkdir(mode=0o700)
    tool = root / 'scripts/recovery/custody.py'
    governance = root / 'services/governance'
    stop()
    recovery.restore('governance', 'governance-current')
    old_credential = Path(environments['governance']['CONSOLE_CREDENTIAL_FILE']).read_text()
    current_credential = secrets.token_hex(32)
    private_values.append(current_credential)
    phrase = secrets.token_urlsafe(32)
    private_values.append(phrase)
    phrase_file = directory / 'phrase'
    phrase_file.write_text(phrase); phrase_file.chmod(0o600)
    principals, keys = [], []
    for number, role in enumerate(['recovery_owner', 'security_reviewer']):
        key = directory / f'synthetic-key-{number}.pem'
        run(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:3072', '-aes-256-cbc',
             '-pass', 'file:' + str(phrase_file), '-out', str(key)])
        key.chmod(0o600)
        public = run(['openssl', 'pkey', '-in', str(key), '-passin', 'file:' + str(phrase_file), '-pubout'])
        keys.append(key)
        principals.append({'id': str(uuid.uuid4()), 'role': role, 'public_key_pem': public})
    original = Path(environments['governance']['GOVERNANCE_IDENTITY_ADMISSION_FILE'])
    installation = json.loads(original.read_text())['installation_id']
    policy = {'version': 1, 'installation_id': installation, 'valid_from': int(time.time()) - 10,
              'valid_until': int(time.time()) + 3600, 'principals': principals}
    trust_input = directory / 'trust.json'
    custody.write_new(trust_input, custody.canonical(policy))
    store = directory / 'independent-custody'
    run(['python', str(tool), 'enroll', '--directory', str(store), '--admission', str(original), '--trust', str(trust_input)], label='recovery-custody-enroll')
    run(['python', str(tool), 'hold', '--directory', str(store), '--case-reference', 'SYNTHETIC-P02-RECOVERY'], label='recovery-custody-hold')
    admission_path = store / 'public/identity-admission.json'
    trust_path = store / 'public/trust.json'
    for environment in [environments['governance'], owner_environment]:
        environment.update(GOVERNANCE_IDENTITY_ADMISSION_FILE=str(admission_path), GOVERNANCE_IDENTITY_RECOVERY_TRUST_FILE=str(trust_path))
    Path(environments['governance']['CONSOLE_CREDENTIAL_FILE']).write_text(current_credential)
    member = json.loads(sql("SELECT row_to_json(m) FROM app.tenant_memberships m WHERE state='active' AND role='tenant_admin' AND site_id IS NULL AND environment IS NULL ORDER BY tenant_id LIMIT 1;", 'governance').strip())
    observations = {'case_reference': 'SYNTHETIC-P02-RECOVERY',
                    'restore_sha256': hashlib.sha256((private / 'governance-current.dump').read_bytes()).hexdigest(),
                    'records_sha256': hashlib.sha256(b'Synthetic current owner, retirement, revocation and provider records; not production custody').hexdigest(),
                    'containment_sha256': hashlib.sha256(b'Disposable applications stopped and notification pump drained').hexdigest(),
                    'previous_workloads': {'console': hashlib.sha256(old_credential.encode()).hexdigest(), 'catalogue': None, 'planning': None, 'assurance': None},
                    'memberships': [{'id': member['id'], 'owner_record_sha256': hashlib.sha256(b'Synthetic tenant-owner reconciliation approval').hexdigest()}]}
    inputs = directory / 'observations.json'
    custody.write_new(inputs, custody.canonical(observations))

    def action(operation, name, source=None, recovery_id=None, environment=None, expected=0):
        output = directory / (name + '.json')
        command = ['php', '-d', 'curl.cainfo=' + str(provider.certificate), 'artisan', 'identity:recovery', operation, '--output=' + str(output)]
        if source:
            command.append('--input=' + str(source))
        if recovery_id:
            command.append('--recovery-id=' + recovery_id)
        run(command, cwd=governance, env=environment or owner_environment, expected=expected, label='recovery-' + name)
        return output

    def sign_pair(plan, prefix):
        paths = []
        for number, principal in enumerate(principals):
            target = directory / f'{prefix}-signature-{number}.json'
            master, slave = pty.openpty()
            process = subprocess.Popen(['python', str(tool), 'sign', '--trust', str(trust_path), '--payload', str(plan),
                                        '--principal', principal['id'], '--key', str(keys[number]), '--output', str(target)],
                                       stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
            os.close(slave)
            body, sent, deadline = b'', False, time.monotonic() + 20
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        try:
                            chunk = os.read(master, 4096)
                        except OSError:
                            break
                        if not chunk:
                            break
                        body += chunk
                        if b'passphrase:' in body and not sent:
                            os.write(master, phrase.encode() + b'\n'); sent = True
                    elif process.poll() is not None:
                        break
                check('custody-encrypted-key-signs-' + prefix + '-' + str(number), process.wait(timeout=2) == 0 and sent and phrase.encode() not in body)
            finally:
                os.close(master)
                if process.poll() is None:
                    process.kill(); process.wait()
            paths.append(target)
        envelope = directory / (prefix + '-envelope.json')
        run(['python', str(tool), 'assemble', '--trust', str(trust_path), '--payload', str(plan),
             '--signature', str(paths[0]), '--signature', str(paths[1]), '--output', str(envelope)], label='recovery-' + prefix + '-assembled')
        return envelope

    before = recovery.fingerprint('governance')
    action('prepare', 'runtime-denied', inputs, environment=environments['governance'], expected=1)
    check('runtime-cannot-enter-owner-recovery', recovery.fingerprint('governance') == before)
    for name, statement in [
        ('binding', "UPDATE app.identity_admission SET binding_sha256 = repeat('0',64);"),
        ('bootstrap-function-rebind', "SELECT app.bind_initial_identity_admission(repeat('0',64));"),
        ('receipt-insert', "INSERT INTO app.identity_recovery_receipts(id) VALUES ('550e8400-e29b-41d4-a716-446655440040');"),
        ('receipt-delete', 'DELETE FROM app.identity_recovery_receipts;'),
        ('release-insert', "INSERT INTO app.identity_recovery_releases(id) VALUES ('550e8400-e29b-41d4-a716-446655440040');")]:
        message = sql(statement, 'governance', 'governance_runtime', environments['governance']['DB_PASSWORD'], expected=3)
        check('runtime-recovery-denial-' + name, 'permission denied' in message or 'identity_recovery_held' in message)
    plan_file = action('prepare', 'prepared', inputs)
    plan = custody.decode(custody.read(plan_file, private=True))
    envelope = sign_pair(plan_file, 'reconcile')
    packet = custody.decode(custody.read(envelope, private=True))
    single = directory / 'single-approval.json'
    custody.write_new(single, custody.canonical(packet | {'signatures': packet['signatures'][:1]}))
    action('apply', 'one-approver-denied', single, expected=1)
    check('one-approver-cannot-change-restored-state', recovery.fingerprint('governance') == before)
    receipt_file = action('apply', 'applied', envelope)
    receipt = custody.decode(custody.read(receipt_file, private=True))
    check('reconciliation-committed-but-held', receipt['admission'] == 'HELD' and custody.admission(store)['state'] == 'held')
    check('restored-sessions-are-all-revoked', sql("SELECT count(*) FROM app.federated_sessions WHERE revoked_at IS NULL;", 'governance').strip() == '0')
    check('only-current-owner-reconciled-membership-retained', sql("SELECT count(*) FROM app.tenant_memberships WHERE state='active';", 'governance').strip() == '1')
    held_bytes = admission_path.read_bytes()
    custody.atomic(admission_path, custody.canonical(custody.admission(store) | {'state': 'active'}), 0o444)
    start()
    wire('/identity/session', 'Error', expected=503, token=initial_session, workload=current_credential)
    stop()
    custody.atomic(admission_path, held_bytes.rstrip(b'\n'), 0o444)
    resume_file = action('resume-plan', 'resume-prepared', recovery_id=plan['recovery_id'])
    resume_envelope = sign_pair(resume_file, 'resume')
    confirmation_file = action('confirm', 'resume-confirmed', resume_envelope)
    current = recovery.fingerprint('governance')
    archive = recovery.capture('governance', 'governance-reconciled')
    recovery.restore('governance', 'governance-reconciled')
    check('recovery-signatures-receipts-and-releases-survive-full-schema-restore', recovery.fingerprint('governance') == current)
    for name, statement in [('receipt-update', "UPDATE app.identity_recovery_receipts SET plan_sha256=repeat('0',64);"),
                            ('release-update', "UPDATE app.identity_recovery_releases SET envelope_sha256=repeat('0',64);"),
                            ('release-delete', 'DELETE FROM app.identity_recovery_releases;')]:
        denial = sql(statement, 'governance', 'governance_runtime', environments['governance']['DB_PASSWORD'], expected=3)
        check('runtime-cannot-rewrite-' + name, 'permission denied' in denial)
    run(['python', str(tool), 'resume', '--directory', str(store), '--envelope', str(resume_envelope), '--confirmation', str(confirmation_file)], label='recovery-independent-release')
    run(['python', str(tool), 'verify', '--directory', str(store)], label='recovery-custody-final-verification')
    start()
    wire('/identity/session', 'Error', expected=401, token=initial_session, workload=current_credential)
    wire('/identity/session', 'Error', expected=401, token=initial_session, workload=old_credential)

    def request(path, body):
        request = urllib.request.Request('http://127.0.0.1:8032' + path, data=json.dumps(body).encode(),
                                        headers={'Authorization': 'Bearer ' + current_credential, 'Content-Type': 'application/json', 'Accept': 'application/json'})
        with urllib.request.urlopen(request, timeout=5) as response:
            check('recovered-' + path, response.status == 200 and 'no-store' in response.headers.get('Cache-Control', ''))
            return json.loads(response.read())

    browser_binding = secrets.token_hex(32)
    flow = request('/identity/oidc/flows', {'purpose': 'login', 'browser_binding': browser_binding})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(provider.certificate))), NoRedirect)
    with opener.open(flow['authorization_url'], timeout=5) as response:
        page = response.read().decode()
    attempt = re.search(r'name="attempt" value="([0-9a-f]{64})"', page)[1]
    authorization = urllib.request.Request(provider.issuer + '/authorize', data=urllib.parse.urlencode({'attempt': attempt, 'subject': 'p02-admin'}).encode())
    try:
        opener.open(authorization, timeout=5)
        raise RuntimeError('provider did not issue the expected callback')
    except urllib.error.HTTPError as response:
        check('fresh-recovery-provider-redirect', response.code == 303)
        callback = {key: values[0] for key, values in urllib.parse.parse_qs(urllib.parse.urlsplit(response.headers['Location']).query).items()}
    session = request('/identity/oidc/callback', callback | {'browser_binding': browser_binding})['session_token']
    private_values.append(session)
    wire('/identity/session', 'CurrentIdentity', token=session, workload=current_credential)
    check('fresh-recovery-session-is-the-only-live-session', sql('SELECT count(*) FROM app.federated_sessions WHERE revoked_at IS NULL;', 'governance').strip() == '1')
    stop()
    run(['python', str(tool), 'hold', '--directory', str(store), '--case-reference', 'SYNTHETIC-RECONTAIN'], label='recovery-hold-after-resumption')
    recovery.restore('governance', 'governance-reconciled')
    start()
    wire('/identity/session', 'Error', expected=503, token=session, workload=current_credential)
    check('later-hold-defeats-restored-confirmed-authority', custody.admission(store)['state'] == 'held')
    return {'scope': 'Real migration-owner PostgreSQL reconciliation, encrypted independent signing keys, separate custodian process, explicit release, fresh HTTPS OIDC admission and complete reconciled-schema restore',
            'plan_sha256': custody.digest(plan), 'reconcile_envelope_sha256': custody.digest(packet),
            'resume_envelope_sha256': hashlib.sha256(custody.read(resume_envelope, private=True)).hexdigest(),
            'reconciled_archive_sha256': archive, 'reconciled_table_fingerprints': current,
            'custody_journal_sha256': hashlib.sha256((store / 'journal.jsonl').read_bytes()).hexdigest(),
            'limits': ['Synthetic operator identities and current owner records; no production custodian appointment',
                       'Disposable filesystem custody; no production off-host mount/backup/host-administration separation proven',
                       'No local bootstrap recovery, native effect, production key-service recovery, HA or accepted RTO/RPO']}
