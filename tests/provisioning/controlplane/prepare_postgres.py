"""Provision isolated PostgreSQL test roles and grants for CI.

Uses only test DSNs. Never run against a production database. The admin
connection provisions roles; a separate non-superuser owner runs migrations.
"""
from __future__ import annotations

import os


def main() -> int:
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict

    admin_dsn = os.environ['HOSTING_TEST_POSTGRES_ADMIN_DSN']
    migration_dsn = os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
    runtime_dsn = os.environ['HOSTING_TEST_POSTGRES_RUNTIME_DSN']
    authority_dsn = os.environ.get('HOSTING_TEST_POSTGRES_AUTHORITY_DSN')
    from provisioner.controlplane.persistence.migrate import apply_migrations

    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        admin_role = connection.execute('SELECT current_user').fetchone()[0]
        database = connection.execute('SELECT current_database()').fetchone()[0]
        identities = [migration_dsn, runtime_dsn]
        if authority_dsn:
            identities.append(authority_dsn)
        roles = []
        for dsn in identities:
            settings = conninfo_to_dict(dsn)
            role_name, password = settings.get('user'), settings.get('password')
            if not role_name or not password or role_name == admin_role:
                raise ValueError('Test roles require distinct users and passwords')
            if role_name in roles:
                raise ValueError('Test migration/runtime/authority roles must be separate')
            roles.append(role_name)
            role = sql.Identifier(role_name)
            secret = sql.Literal(password)
            exists = connection.execute('SELECT 1 FROM pg_roles WHERE rolname = %s',
                                        (role_name,)).fetchone()
            command = 'ALTER ROLE' if exists else 'CREATE ROLE'
            connection.execute(sql.SQL(
                command + ' {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}'
            ).format(role, secret))
            connection.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(
                sql.Identifier(database), role))
        connection.execute(sql.SQL('GRANT CREATE ON DATABASE {} TO {}').format(
            sql.Identifier(database), sql.Identifier(roles[0])))
        apply_migrations(lambda: psycopg.connect(migration_dsn))
        for role_name in roles[1:]:
            connection.execute(sql.SQL('GRANT USAGE ON SCHEMA hosting_controlplane TO {}').format(
                sql.Identifier(role_name)))

        runtime = sql.Identifier(roles[1])
        for statement in (
            'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.enterprise_records TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.enterprise_record_history TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.audit_events TO {}',
            'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.native_ownership TO {}',
            'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.operation_jobs, '
            'hosting_controlplane.job_outbox TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.job_events TO {}',
            'GRANT SELECT ON hosting_controlplane.plan_authority_state, '
            'hosting_controlplane.plan_approvals, hosting_controlplane.plan_revocations TO {}',
            'GRANT EXECUTE ON FUNCTION '
            'hosting_controlplane.lock_authority_scope(text, text, text) TO {}',
            'GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO {}',
        ):
            connection.execute(sql.SQL(statement).format(runtime))
        if authority_dsn:
            writer = sql.Identifier(roles[2])
            for statement in (
                'GRANT SELECT ON hosting_controlplane.enterprise_records, '
                'hosting_controlplane.audit_events TO {}',
                'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.plan_authority_state TO {}',
                'GRANT SELECT, INSERT ON hosting_controlplane.plan_approvals, '
                'hosting_controlplane.plan_revocations TO {}',
                'GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.lock_authority_scope(text, text, text) TO {}',
                'GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO {}',
            ):
                connection.execute(sql.SQL(statement).format(writer))
    print('PostgreSQL control-plane test roles and grants are ready')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
