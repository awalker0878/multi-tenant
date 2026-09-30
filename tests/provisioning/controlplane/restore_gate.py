"""Disposable PostgreSQL dump/restore gate for control-plane durability.

Run explicitly after the normal database integration tests in the isolated CI
PostgreSQL service: ``python -m tests.provisioning.controlplane.restore_gate``.
This is deliberately not included in unittest discovery and never targets a
production database. It uses the PostgreSQL 17 client inside the service
container to avoid host/client version drift.
"""
from __future__ import annotations

import os
import subprocess
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from provisioner.controlplane.persistence import (
    AuditContext, EnterpriseRecordStore, NativeBinding, TenantContext,
)
from provisioner.controlplane.persistence.migrate import apply_migrations
from tests.provisioning.schema.test_enterprise_records import SOURCE, binding, workload


REQUIRED_TABLES = (
    'enterprise_records', 'enterprise_record_history', 'audit_events',
    'native_ownership', 'schema_migrations', 'application_draft_revisions', 'assessment_inputs',
)


def _container() -> str:
    configured = os.environ.get('HOSTING_TEST_POSTGRES_CONTAINER_ID')
    if configured:
        return configured
    result = subprocess.run(
        ['docker', 'ps', '--filter', 'ancestor=postgres:17', '--format', '{{.ID}}'],
        check=True, capture_output=True, text=True)
    candidates = result.stdout.splitlines()
    if len(candidates) != 1:
        raise RuntimeError('Restore gate requires exactly one PostgreSQL 17 service container')
    return candidates[0]


def _client(container: str, password: str, command: str, user: str,
            database: str, archive: Path, *, section: str | None = None) -> None:
    argv = ['docker', 'exec', '-i', '-e', 'PGPASSWORD=' + password,
            container, command, '--host=localhost', '--username=' + user,
            '--dbname=' + database]
    if command == 'pg_dump':
        argv += ['--format=custom', '--no-owner', '--no-acl',
                 '--schema=hosting_controlplane']
        with archive.open('wb') as output:
            subprocess.run(argv, stdout=output, stderr=subprocess.PIPE, check=True)
    else:
        argv += ['--no-owner', '--no-acl', '--exit-on-error', '--section=' + section]
        with archive.open('rb') as source:
            subprocess.run(argv, stdin=source, stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE, check=True)


def _snapshot(connection) -> dict:
    from psycopg import sql

    tables = connection.execute(
        "SELECT c.relname FROM pg_catalog.pg_class c "
        "JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'hosting_controlplane' AND c.relkind = 'r' "
        'ORDER BY c.relname').fetchall()
    names = [name for (name,) in tables]
    if not set(REQUIRED_TABLES) <= set(names):
        raise AssertionError('Core control-plane tables are missing')
    # This is a disposable CI database, and the snapshot uses the authorized
    # backup/admin role to inspect every tenant and every migration-owned table.
    result = {'tables': {}}
    for table in names:
        rows = connection.execute(sql.SQL('SELECT * FROM hosting_controlplane.{}').format(
            sql.Identifier(table))).fetchall()
        result['tables'][table] = sorted(rows, key=repr)
    result['migration_ledger'] = connection.execute(
        'SELECT version, script_digest FROM hosting_controlplane.schema_migrations '
        'ORDER BY version').fetchall()
    result['sequences'] = connection.execute(
        "SELECT sequencename, last_value FROM pg_catalog.pg_sequences "
        "WHERE schemaname = 'hosting_controlplane' ORDER BY sequencename"
    ).fetchall()
    result['rls'] = connection.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
        "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n "
        "ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'hosting_controlplane' AND c.relkind = 'r' "
        'ORDER BY c.relname').fetchall()
    return result


def _unsafe_public_definer_functions(connection) -> list[str]:
    rows = connection.execute(
        "SELECT p.proname FROM pg_catalog.pg_proc p "
        "JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'hosting_controlplane' AND p.prosecdef "
        "AND EXISTS (SELECT 1 FROM pg_catalog.aclexplode(" 
        "COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))) a "
        "WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE') "
        'ORDER BY p.proname').fetchall()
    return [name for (name,) in rows]


def main() -> int:
    if os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') != '1':
        raise RuntimeError('Restore gate runs only against the disposable CI database')
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    admin_dsn = os.environ['HOSTING_TEST_POSTGRES_ADMIN_DSN']
    migration_dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
    runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
    admin_info = conninfo_to_dict(admin_dsn)
    migration_info = conninfo_to_dict(migration_dsn)
    original_db = admin_info['dbname']
    if original_db != 'hosting_controlplane_test':
        raise RuntimeError('Restore gate requires the named disposable CI database')
    restore_db = 'hosting_restore_' + uuid4().hex[:16]
    container = _container()
    suffix = uuid4().hex[:14]
    ctx = TenantContext('restore-org-' + suffix, 'restore-tenant')
    audit = AuditContext('issuer|https://idp.example/restore-operator',
                         'restore-' + suffix)
    record = workload()
    record['metadata'].update(organizationId=ctx.organization_id,
                              tenantId=ctx.tenant_id,
                              workloadId='restore-workload-' + suffix)
    native_id = 'restore-vm-' + suffix
    record['spec']['machines'][0]['bindings'][0]['binding']['nativeId'] = native_id
    store = EnterpriseRecordStore(lambda: psycopg.connect(runtime_dsn))
    saved = store.create(ctx, record, audit)
    scope = deepcopy(SOURCE)
    scope.update(organizationId=ctx.organization_id, tenantId=ctx.tenant_id)
    lease = store.acquire_owner_lease(ctx, scope,
                                      NativeBinding.from_record(binding('vm', native_id)),
                                      record['metadata']['workloadId'], 'restore-worker',
                                      3600, audit)
    if lease.epoch != 1 or saved.revision != 1:
        raise AssertionError('Restore fixture did not persist its baseline')

    restored_admin_dsn = make_conninfo(admin_dsn, dbname=restore_db)
    restored_migration_dsn = make_conninfo(migration_dsn, dbname=restore_db)
    restored_runtime_dsn = make_conninfo(runtime_dsn, dbname=restore_db)
    with psycopg.connect(admin_dsn) as source:
        before = _snapshot(source)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
            sql.Identifier(restore_db), sql.Identifier(migration_info['user'])))
    try:
        with TemporaryDirectory(prefix='hosting-restore-') as directory:
            archive = Path(directory) / 'controlplane.dump'
            _client(container, admin_info['password'], 'pg_dump',
                    admin_info['user'], original_db, archive)
            _client(container, migration_info['password'], 'pg_restore',
                    migration_info['user'], restore_db, archive, section='pre-data')
            # A migration owner is deliberately subject to FORCE RLS. Restore
            # into a disconnected DB and keep RLS disabled only during COPY;
            # compare/re-enable every original policy flag before exposure.
            with psycopg.connect(restored_migration_dsn) as restored_owner:
                for table, rls, _force in before['rls']:
                    if rls:
                        restored_owner.execute(sql.SQL(
                            'ALTER TABLE hosting_controlplane.{} DISABLE ROW LEVEL SECURITY'
                        ).format(sql.Identifier(table)))
            _client(container, migration_info['password'], 'pg_restore',
                    migration_info['user'], restore_db, archive, section='data')
            _client(container, migration_info['password'], 'pg_restore',
                    migration_info['user'], restore_db, archive, section='post-data')
            with psycopg.connect(restored_migration_dsn) as restored_owner:
                for table, rls, force in before['rls']:
                    if rls:
                        restored_owner.execute(sql.SQL(
                            'ALTER TABLE hosting_controlplane.{} ENABLE ROW LEVEL SECURITY'
                        ).format(sql.Identifier(table)))
                    if force:
                        restored_owner.execute(sql.SQL(
                            'ALTER TABLE hosting_controlplane.{} FORCE ROW LEVEL SECURITY'
                        ).format(sql.Identifier(table)))
                # --no-acl intentionally omits runtime grants, but also omits
                # source REVOKEs. Reapply deny-first defaults before inspection.
                restored_owner.execute(
                    'REVOKE ALL ON SCHEMA hosting_controlplane FROM PUBLIC')
                restored_owner.execute(
                    'REVOKE ALL ON ALL TABLES IN SCHEMA hosting_controlplane FROM PUBLIC')
                restored_owner.execute(
                    'REVOKE ALL ON ALL SEQUENCES IN SCHEMA hosting_controlplane FROM PUBLIC')
                restored_owner.execute(
                    'REVOKE ALL ON ALL FUNCTIONS IN SCHEMA hosting_controlplane FROM PUBLIC')

        with psycopg.connect(restored_admin_dsn) as restored_admin:
            after = _snapshot(restored_admin)
            public_definers = _unsafe_public_definer_functions(restored_admin)
            owner = restored_admin.execute(
                "SELECT r.rolsuper, r.rolbypassrls "
                "FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n "
                "ON n.oid = p.pronamespace "
                "JOIN pg_catalog.pg_roles r ON r.oid = p.proowner "
                "WHERE n.nspname = 'hosting_controlplane' "
                "AND p.proname = 'lock_authority_scope'").fetchone()
        if before != after:
            raise AssertionError('Restored record, history, audit, ownership, '
                                 'sequence state, migration ledger, or RLS flags differ')
        if owner != (False, False):
            raise AssertionError('Restored authority function owner bypasses row security')
        if public_definers:
            raise AssertionError('Restored SECURITY DEFINER functions are PUBLIC executable')
        if apply_migrations(lambda: psycopg.connect(restored_migration_dsn)) != []:
            raise AssertionError('Restored migration ledger was not current')
        # --no-acl omits runtime grants. This site remains observation-only
        # until native resources and epochs have been reconciled by B44.
        with psycopg.connect(restored_runtime_dsn) as runtime:
            try:
                runtime.execute('SELECT count(*) FROM hosting_controlplane.enterprise_records')
            except psycopg.errors.InsufficientPrivilege:
                pass
            else:
                raise AssertionError('Restored database unexpectedly permits runtime access')
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(
                sql.Identifier(restore_db)))
    print('PostgreSQL dump/restore preserved scoped state and remained observation-only')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
