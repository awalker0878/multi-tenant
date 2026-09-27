"""Upgrade an isolated pre-0012 database containing worker audit history."""
from __future__ import annotations

import hashlib
import os
import unittest
from importlib import resources
from uuid import uuid4

from provisioner.controlplane.persistence.migrate import apply_migrations


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') == '1' and
                     os.environ.get('HOSTING_TEST_POSTGRES_ADMIN_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN'),
                     'Requires the disposable PostgreSQL CI database')
class MigrationUpgradeTests(unittest.TestCase):
    def test_worker_audit_history_survives_directory_migration(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        admin_dsn = os.environ['HOSTING_TEST_POSTGRES_ADMIN_DSN']
        migration_dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        admin_info = conninfo_to_dict(admin_dsn)
        if admin_info.get('dbname') != 'hosting_controlplane_test':
            raise RuntimeError('Upgrade gate requires the named disposable CI database')
        name = 'hosting_upgrade_' + uuid4().hex[:16]
        owner = conninfo_to_dict(migration_dsn)['user']
        upgraded_dsn = make_conninfo(migration_dsn, dbname=name)
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
                sql.Identifier(name), sql.Identifier(owner)))
        try:
            migrations = resources.files(
                'provisioner.controlplane.persistence.migrations')
            scripts = sorted(item for item in migrations.iterdir()
                             if item.name[:4].isdigit() and item.name.endswith('.sql'))
            with psycopg.connect(upgraded_dsn, autocommit=True) as connection:
                for item in scripts:
                    version = item.name[:4]
                    if version > '0011':
                        break
                    script = item.read_text(encoding='utf-8')
                    digest = hashlib.sha256(script.encode('utf-8')).hexdigest()
                    with connection.transaction():
                        connection.execute(script, prepare=False)
                        connection.execute(
                            'INSERT INTO hosting_controlplane.schema_migrations '
                            '(version, script_digest) VALUES (%s, %s)',
                            (version, digest))
                with connection.transaction():
                    connection.execute(
                        "SELECT set_config('app.organization_id', 'upgrade-org', true), "
                        "set_config('app.tenant_id', 'upgrade-tenant', true)")
                    for action in ('WORKER_CERT_ENROLL', 'WORKER_CERT_ROTATE',
                                   'WORKER_CERT_REVOKE', 'WORKER_REVOKE'):
                        connection.execute(
                            'INSERT INTO hosting_controlplane.audit_events '
                            '(organization_id, tenant_id, actor_id, correlation_id, '
                            'action, record_kind, record_id, revision, record_digest) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                            ('upgrade-org', 'upgrade-tenant', 'upgrade-operator',
                             'upgrade-worker-history', action, 'WorkerEnrollment',
                             'worker-1', 1, 'a' * 64))
            changed = apply_migrations(lambda: psycopg.connect(upgraded_dsn))
            self.assertIn('0012', changed)
            with psycopg.connect(upgraded_dsn) as connection:
                connection.execute(
                    "SELECT set_config('app.organization_id', 'upgrade-org', true), "
                    "set_config('app.tenant_id', 'upgrade-tenant', true)")
                actions = connection.execute(
                    'SELECT action FROM hosting_controlplane.audit_events '
                    'ORDER BY audit_sequence').fetchall()
                self.assertEqual([row[0] for row in actions], [
                    'WORKER_CERT_ENROLL', 'WORKER_CERT_ROTATE',
                    'WORKER_CERT_REVOKE', 'WORKER_REVOKE'])
            self.assertEqual(apply_migrations(
                lambda: psycopg.connect(upgraded_dsn)), [])
        finally:
            with psycopg.connect(admin_dsn, autocommit=True) as admin:
                admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(
                    sql.Identifier(name)))


if __name__ == '__main__':
    unittest.main()
