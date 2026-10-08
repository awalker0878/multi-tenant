"""Bounded PostgreSQL snapshot/restart checks in the disposable P02 campaign.

Database archives and keys remain private and are destroyed with the environment.
This does not implement an operator's recovery authorization or reconcile a stale
snapshot: it proves stale state stays quarantined under independent current custody.
"""
import hashlib
import json
import re
import secrets


class IdentityRecovery:
    def __init__(self, container, private, run, sql, check):
        self.container, self.private = container, private
        self.run, self.sql, self.check = run, sql, check

    def capture(self, database, name):
        self.run(['docker', 'exec', self.container, 'pg_dump', '-U', 'postgres', '-d', database,
                  '--schema=app', '--format=custom', '--file=/tmp/' + name + '.dump'])
        path = self.private / (name + '.dump')
        self.run(['docker', 'cp', self.container + ':/tmp/' + name + '.dump', str(path)])
        path.chmod(0o600)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def restore(self, database, name):
        self.sql('DROP SCHEMA app CASCADE;', database)
        self.run(['docker', 'exec', self.container, 'pg_restore', '-U', 'postgres', '-d', database,
                  '--exit-on-error', '/tmp/' + name + '.dump'])

    def fingerprint(self, database):
        tables = self.sql("SELECT tablename FROM pg_tables WHERE schemaname='app' ORDER BY tablename;", database).splitlines()
        result = {}
        for table in tables:
            if not re.fullmatch('[a-z_]+', table):
                raise RuntimeError('unexpected_recovery_table')
            rows = sorted(self.sql('SELECT row_to_json(t)::text FROM app.' + table + ' t;', database).splitlines())
            result[table] = {'rows': len(rows), 'sha256': hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
        return result

    def qualify(self, stop, start, wire, admission, admission_file, initial_session, temporary, bootstrap):
        archives, before = {}, {}
        stop()
        for database in ['governance', 'console']:
            archives[database] = self.capture(database, database + '-current')
            before[database] = self.fingerprint(database)
        start()
        for database in before:
            self.check(database + '-restart-preserves-every-owned-table', self.fingerprint(database) == before[database])
        wire('/identity/session', 'Error', expected=401, token=initial_session)
        self.check('retired-bootstrap-stays-retired-after-process-restart', 'Temporary password:' not in bootstrap())
        stop()
        # Complete application schemas, not a selected audit row or a counter.
        for database in before:
            self.restore(database, database + '-current')
            self.check(database + '-database-restore-preserves-every-owned-table', self.fingerprint(database) == before[database])
        start()
        wire('/identity/session', 'Error', expected=401, token=initial_session)
        wire('/identity/local-sessions', 'Error', expected=401, body={'username': 'admin', 'password': temporary})
        self.check('retired-bootstrap-stays-retired-after-current-restore', 'Temporary password:' not in bootstrap())
        stop()
        # The restore custodian changes custody BEFORE loading any older application data.
        # Never copy the old descriptor back from a database backup.
        held = admission | {'state': 'held', 'epoch': secrets.token_hex(32), 'bootstrap_allowed': False}
        admission_file.write_text(json.dumps(held))
        self.restore('governance', 'governance-before-activation')
        start()
        for state in ['held', 'active']:
            held['state'] = state
            admission_file.write_text(json.dumps(held))
            # Even making custody active cannot adopt the old generation automatically.
            wire('/identity/local-sessions', 'Error', expected=503, body={'username': 'admin', 'password': temporary})
            wire('/identity/session', 'Error', expected=503, token=initial_session)
            wire('/identity/oidc/flows', 'Error', expected=503, body={'purpose': 'login', 'browser_binding': 'a' * 64})
            self.check('stale-restore-bootstrap-denied-' + state, 'Identity admission is held' in bootstrap(expected=1))
        self.check('stale-restore-did-not-rebind-or-reset', self.sql('SELECT count(*) FROM app.identity_audit;', 'governance').strip() == '2')
        return {'scope': 'all owned Governance/Console application tables; same-key current restore; older identity snapshot quarantined',
                'snapshot_sha256': archives, 'current_table_fingerprints': before,
                'stale_restore_disposition': 'HELD_NO_AUTOMATIC_REBIND',
                'limits': ['No broker-store restore, HA, custody-service deployment or accepted RTO/RPO',
                           'External admission custody must be independently held/rotated before restore; co-restoring an old active descriptor is not protected',
                           'No approval to resume stale authority or to reset bootstrap credentials is inferred']}
