"""Consistent control-DB archives and isolated, observation-only restore checks.

The backup identity is a separate NOSUPERUSER read-only BYPASSRLS custodian.
The restore owner is NOSUPERUSER/NOBYPASSRLS and the destination must have the
explicit isolated database prefix. Runtime grants are never restored. Independent
Object Lock, workflow histories, native epochs and old-writer fencing still need
site reconciliation; equality of this archive cannot enable a native write.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from typing import Callable
from uuid import uuid4

from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

FORMAT = 'hosting-controlplane-backup-manifest/1'
_ISOLATED_DB = re.compile(r'^hosting_observation_restore_[a-z0-9_]{1,48}$')
_SHA = re.compile(r'^[0-9a-f]{64}$')
_REQUIRED = {'enterprise_records', 'enterprise_record_history', 'audit_events',
             'schema_migrations', 'native_ownership', 'operation_jobs',
             'job_outbox', 'native_operation_intents', 'evidence_entries',
             'operating_instance'}


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _digest_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def _tls_dsn(dsn: str) -> dict:
    info = conninfo_to_dict(dsn)
    if (info.get('sslmode') != 'verify-full' or not info.get('host')
            or info['host'].startswith('/') or ',' in info['host']
            or not info.get('dbname') or not info.get('user')):
        raise ValueError('Operating database custody requires exact verify-full TLS')
    return info


def _reviewed_pg_binary(command: str) -> Path:
    """No PATH discovery or unreviewed PostgreSQL client on an operating owner."""
    variables = {'pg_dump': ('HOSTING_PG_DUMP_PATH', 'HOSTING_PG_DUMP_SHA256'),
                 'pg_restore': ('HOSTING_PG_RESTORE_PATH', 'HOSTING_PG_RESTORE_SHA256')}
    if command not in variables:
        raise ValueError('Only reviewed pg_dump/pg_restore archive binaries are permitted')
    path_name, digest_name = variables[command]
    path = Path(os.environ[path_name]).resolve(strict=True)
    allowed = str(path) in ('/usr/bin/' + command, '/usr/local/bin/' + command) or bool(
        re.fullmatch(r'/usr/lib/postgresql/[0-9]{1,2}/bin/' + command, str(path)))
    info = path.stat()
    expected = os.environ[digest_name]
    if (not allowed or not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022
            or not info.st_mode & 0o111 or not _SHA.fullmatch(expected) or _digest_file(path) != expected):
        raise ValueError('Reviewed root-owned PostgreSQL archive binary custody is unavailable')
    return path


def _client(dsn: str, command: str, archive: Path, *, snapshot: str | None = None,
            section: str | None = None, runner: Callable = subprocess.run) -> None:
    info = _tls_dsn(dsn)
    # Do not place passwords in process arguments or command/error output.
    password = info.pop('password', None)
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
    if password is not None:
        env['PGPASSWORD'] = password
    argv = [str(_reviewed_pg_binary(command)), '--dbname=' + make_conninfo(**info), '--no-owner', '--no-acl']
    if command == 'pg_dump':
        if snapshot is None or not re.fullmatch(r'[0-9A-Fa-f-]{1,128}', snapshot):
            raise ValueError('A current exported PostgreSQL snapshot is required')
        argv += ['--format=custom', '--schema=hosting_controlplane',
                 '--snapshot=' + snapshot]
        mode, direction = 'xb', 'stdout'
    elif command == 'pg_restore' and section in ('pre-data', 'data', 'post-data'):
        argv += ['--exit-on-error', '--section=' + section]
        mode, direction = 'rb', 'stdin'
    else:
        raise ValueError('Only bounded control-plane archive operations are permitted')
    try:
        with archive.open(mode) as stream:
            runner(argv, env=env, **{direction: stream},
                   stderr=subprocess.PIPE, check=True, timeout=3600)
    except subprocess.SubprocessError:
        raise RuntimeError('PostgreSQL archive operation failed; site remains isolated') from None


def snapshot_state(connection) -> dict:
    """Hash every migration-owned table in one externally controlled snapshot."""
    connection.execute("SET LOCAL TIME ZONE 'UTC'")
    connection.execute("SET LOCAL DateStyle='ISO,YMD'")
    tables = connection.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
        "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n "
        "ON n.oid=c.relnamespace WHERE n.nspname='hosting_controlplane' "
        "AND c.relkind='r' ORDER BY c.relname").fetchall()
    if not _REQUIRED <= {row[0] for row in tables}:
        raise ValueError('Control-plane recovery tables are incomplete')
    result = {'tables': {}, 'rls': {}}
    for name, enabled, forced in tables:
        digest = hashlib.sha256()
        count = 0
        query = sql.SQL('SELECT to_jsonb(t)::text FROM hosting_controlplane.{} t '
                        'ORDER BY to_jsonb(t)::text COLLATE "C"').format(sql.Identifier(name))
        with connection.cursor(name='recovery_' + hashlib.sha256(name.encode()).hexdigest()[:16]) as cursor:
            cursor.execute(query)
            for (row,) in cursor:
                raw = row.encode('utf-8')
                digest.update(len(raw).to_bytes(8, 'big'))
                digest.update(raw)
                count += 1
        result['tables'][name] = {'rows': count, 'sha256': digest.hexdigest()}
        result['rls'][name] = {'enabled': enabled, 'forced': forced}
    result['migrationLedger'] = [list(row) for row in connection.execute(
        'SELECT version, script_digest FROM hosting_controlplane.schema_migrations '
        'ORDER BY version').fetchall()]
    result['sequences'] = [list(row) for row in connection.execute(
        "SELECT sequencename,last_value FROM pg_catalog.pg_sequences "
        "WHERE schemaname='hosting_controlplane' ORDER BY sequencename").fetchall()]
    # Epochs, grants, high-water marks, immutable evidence and accepted intents
    # are included in table digests. Do not leak tenant/native identities here.
    return result


def _require_custodian(connection, *, backup: bool) -> None:
    row = connection.execute(
        'SELECT rolsuper,rolbypassrls FROM pg_catalog.pg_roles '
        'WHERE rolname=current_user').fetchone()
    if row != (False, backup):
        raise ValueError('Dedicated backup/restore role separation is required')
    if backup:
        writable = connection.execute(
            "SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n "
            "ON n.oid=c.relnamespace WHERE n.nspname='hosting_controlplane' "
            "AND c.relkind='r' AND (pg_catalog.has_table_privilege(current_user,c.oid,'INSERT') "
            "OR pg_catalog.has_table_privilege(current_user,c.oid,'UPDATE') "
            "OR pg_catalog.has_table_privilege(current_user,c.oid,'DELETE') "
            "OR pg_catalog.has_table_privilege(current_user,c.oid,'TRUNCATE'))").fetchone()[0]
        if writable:
            raise ValueError('Backup custodian must have table SELECT only')


def backup(dsn: str, destination: Path, *, connect: Callable | None = None,
           runner: Callable = subprocess.run) -> dict:
    """Create a dump and manifest without modifying the control database."""
    import psycopg
    _tls_dsn(dsn)
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    archive = destination / 'controlplane.dump'
    connection_factory = connect or (lambda: psycopg.connect(dsn, connect_timeout=5))
    try:
        with connection_factory() as connection:
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            _require_custodian(connection, backup=True)
            snapshot = connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
            state = snapshot_state(connection)
            _client(dsn, 'pg_dump', archive, snapshot=snapshot, runner=runner)
            # PostgreSQL sequences are not MVCC state. If a sequence advanced
            # during the exported-snapshot dump, do not publish a manifest
            # claiming its earlier value matches the archive. Drain/retry via
            # the site operator; the backup identity cannot stop live writers.
            sequences_after = [list(row) for row in connection.execute(
                "SELECT sequencename,last_value FROM pg_catalog.pg_sequences "
                "WHERE schemaname='hosting_controlplane' ORDER BY sequencename").fetchall()]
            if sequences_after != state['sequences']:
                raise RuntimeError('Nontransactional sequence state changed during archive; drain/retry required')
        os.chmod(archive, 0o600)
        manifest = {'format': FORMAT, 'capturedAt': datetime.now(timezone.utc).isoformat(),
                    'archiveSha256': _digest_file(archive), 'state': state,
                    'externalComponents': ['independent-evidence-object-lock-and-vault',
                                           'temporal-history-and-worker-version-routing',
                                           'terraform-backend-versions-and-locks'],
                    'mutationAuthorized': False}
        path = destination / 'manifest.json'
        with path.open('xb') as output:
            os.chmod(path, 0o600)
            output.write(_canonical(manifest) + b'\n')
        return manifest
    except Exception:
        # Leave failed archives for the backup custodian to inspect; never reuse
        # their directory or publish a successful manifest after partial output.
        raise


def compare_restore(manifest: dict, observed: dict) -> dict:
    if (not isinstance(manifest, dict) or set(manifest) != {
            'format', 'capturedAt', 'archiveSha256', 'state', 'externalComponents',
            'mutationAuthorized'} or manifest['format'] != FORMAT
            or manifest['mutationAuthorized'] is not False
            or not _SHA.fullmatch(manifest.get('archiveSha256', ''))
            or not isinstance(manifest['state'], dict)
            or not _REQUIRED <= set(manifest['state'].get('tables', {}))):
        raise ValueError('Immutable control-plane backup manifest is required')
    expected = manifest['state']
    differences = [field for field in ('tables', 'rls', 'migrationLedger', 'sequences')
                   if expected.get(field) != observed.get(field)]
    return {'format': 'hosting-observation-only-restore-report/1',
            'status': 'ARCHIVE_RECONCILED_OBSERVATION_ONLY' if not differences else 'RESTORE_HELD',
            'differences': differences, 'archiveSha256': manifest['archiveSha256'],
            'mutationAuthorized': False,
            'holds': ['INDEPENDENT_EVIDENCE_HIGH_WATER_RECONCILIATION',
                      'TEMPORAL_HISTORY_AND_ACCEPTED_JOB_RECONCILIATION',
                      'NATIVE_OWNER_EPOCH_AND_OLD_WRITER_FENCING',
                      'CURRENT_AUTHORITY_REENROLLMENT_AND_SITE_ACCEPTANCE']}


def restore(dsn: str, source: Path, *, expected_manifest_sha256: str,
            connect: Callable | None = None,
            runner: Callable = subprocess.run) -> dict:
    """Restore only into a pre-created empty, disconnected observation database."""
    import psycopg
    info = _tls_dsn(dsn)
    if not _ISOLATED_DB.fullmatch(info['dbname']):
        raise ValueError('Restore requires an explicitly isolated observation database')
    source = Path(source)
    if not isinstance(expected_manifest_sha256, str) or not _SHA.fullmatch(expected_manifest_sha256):
        raise ValueError('Independent retained manifest digest is required before SQL restore')
    manifest_bytes = (source / 'manifest.json').read_bytes()
    if (len(manifest_bytes) > 4 * 1024**2
            or hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_sha256):
        raise ValueError('Backup manifest differs from independent retained custody')
    manifest = json.loads(manifest_bytes)
    archive = source / 'controlplane.dump'
    if _digest_file(archive) != manifest.get('archiveSha256'):
        raise ValueError('Archive bytes differ from retained manifest')
    compare_restore(manifest, manifest['state'])
    connection_factory = connect or (lambda: psycopg.connect(dsn, connect_timeout=5))
    with connection_factory() as connection:
        _require_custodian(connection, backup=False)
        present = connection.execute(
            "SELECT count(*) FROM pg_catalog.pg_namespace WHERE nspname='hosting_controlplane'"
        ).fetchone()[0]
        connect_grants = connection.execute(
            "SELECT count(*) FROM pg_catalog.aclexplode(COALESCE("
            "(SELECT datacl FROM pg_catalog.pg_database WHERE datname=current_database()),"
            "pg_catalog.acldefault('d',(SELECT datdba FROM pg_catalog.pg_database "
            "WHERE datname=current_database())))) a WHERE a.privilege_type='CONNECT' "
            "AND a.grantee != (SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user)"
        ).fetchone()[0]
        if present or connect_grants:
            raise ValueError('Restore database must be empty with CONNECT revoked from other identities')
    _client(dsn, 'pg_restore', archive, section='pre-data', runner=runner)
    with connection_factory() as connection:
        for table, flags in manifest['state']['rls'].items():
            if flags['enabled']:
                connection.execute(sql.SQL('ALTER TABLE hosting_controlplane.{} '
                    'DISABLE ROW LEVEL SECURITY').format(sql.Identifier(table)))
    _client(dsn, 'pg_restore', archive, section='data', runner=runner)
    _client(dsn, 'pg_restore', archive, section='post-data', runner=runner)
    with connection_factory() as connection:
        # Runtime ACLs are intentionally absent. Do not silently recreate them.
        for object_class in ('TABLES', 'SEQUENCES', 'FUNCTIONS'):
            connection.execute(sql.SQL('REVOKE ALL ON ALL {} IN SCHEMA '
                                      'hosting_controlplane FROM PUBLIC').format(sql.SQL(object_class)))
        connection.execute('REVOKE ALL ON SCHEMA hosting_controlplane FROM PUBLIC')
        # Owner inspects while RLS is disabled only in this disconnected restore.
        for table in manifest['state']['rls']:
            connection.execute(sql.SQL('ALTER TABLE hosting_controlplane.{} '
                'DISABLE ROW LEVEL SECURITY').format(sql.Identifier(table)))
        observed = snapshot_state(connection)
        for table, flags in manifest['state']['rls'].items():
            if flags['enabled']:
                connection.execute(sql.SQL('ALTER TABLE hosting_controlplane.{} '
                    'ENABLE ROW LEVEL SECURITY').format(sql.Identifier(table)))
            if flags['forced']:
                connection.execute(sql.SQL('ALTER TABLE hosting_controlplane.{} '
                    'FORCE ROW LEVEL SECURITY').format(sql.Identifier(table)))
        # Compare the reapplied flags rather than the temporary COPY settings.
        observed['rls'] = {name: {'enabled': enabled, 'forced': forced} for name, enabled, forced in
            connection.execute("SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity "
                "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='hosting_controlplane' AND c.relkind='r' ORDER BY c.relname").fetchall()}
        # Compare the original retained bytes first, including the archived
        # instance row. Then rotate only this restored control-instance identity.
        # The old database OID already blocks claims even before quarantine.
        report = compare_restore(manifest, observed)
        from .instance import quarantine
        report['instanceInterlock'] = quarantine(connection, manifest_sha256=expected_manifest_sha256)
        connection.execute(sql.SQL('ALTER DATABASE {} SET default_transaction_read_only=on')
                           .format(sql.Identifier(info['dbname'])))
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('backup', 'restore'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--new-archive', action='store_true',
                        help='Create a unique archive below the configured backup directory')
    args = parser.parse_args(argv)
    try:
        dsn = os.environ['HOSTING_BACKUP_DSN' if args.mode == 'backup' else 'HOSTING_RESTORE_DSN']
        directory = args.directory
        if args.new_archive:
            if args.mode != 'backup':
                raise ValueError('Fresh archive naming applies only to backup')
            directory = directory / ('controlplane-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                                     + '-' + uuid4().hex)
        result = (backup(dsn, directory) if args.mode == 'backup' else
                  restore(dsn, args.directory,
                          expected_manifest_sha256=os.environ['HOSTING_RESTORE_MANIFEST_SHA256']))
        if args.mode == 'backup':
            result = {'status': 'CONTROL_DB_ARCHIVE_CREATED_NOT_FULL_DR_ACCEPTANCE',
                      'archiveDirectory': str(directory), **result}
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get('status') != 'RESTORE_HELD' else 2
    except Exception:
        print(json.dumps({'status': 'RECOVERY_HELD', 'mutationAuthorized': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
