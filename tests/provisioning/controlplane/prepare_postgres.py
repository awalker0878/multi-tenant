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
    enrollment_dsn = os.environ.get('HOSTING_TEST_POSTGRES_ENROLLMENT_DSN')
    directory_resolver_dsn = os.environ.get('HOSTING_TEST_POSTGRES_DIRECTORY_RESOLVER_DSN')
    directory_writer_dsn = os.environ.get('HOSTING_TEST_POSTGRES_DIRECTORY_WRITER_DSN')
    site_worker_dsn = os.environ.get('HOSTING_TEST_POSTGRES_SITE_WORKER_DSN')
    discovery_dsn = os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN')
    assessment_dsn = os.environ.get('HOSTING_TEST_POSTGRES_ASSESSMENT_DSN')
    from provisioner.controlplane.persistence.migrate import apply_migrations

    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        admin_role = connection.execute('SELECT current_user').fetchone()[0]
        database = connection.execute('SELECT current_database()').fetchone()[0]
        if connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = 'hosting_site_worker_roles'"
        ).fetchone() is None:
            connection.execute(
                'CREATE ROLE hosting_site_worker_roles NOLOGIN NOSUPERUSER NOBYPASSRLS')
        identities = [dsn for dsn in (
            migration_dsn, runtime_dsn, authority_dsn, enrollment_dsn,
            directory_resolver_dsn, directory_writer_dsn, site_worker_dsn,
            discovery_dsn, assessment_dsn) if dsn]
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
            if dsn == site_worker_dsn:
                connection.execute(sql.SQL('GRANT hosting_site_worker_roles TO {}').format(role))
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
            'GRANT SELECT ON hosting_controlplane.audit_streams TO {}',
            'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.native_ownership TO {}',
            'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.operation_jobs, '
            'hosting_controlplane.job_outbox TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.job_events TO {}',
            'GRANT SELECT ON hosting_controlplane.plan_authority_state, '
            'hosting_controlplane.plan_approvals, hosting_controlplane.plan_revocations TO {}',
            'GRANT EXECUTE ON FUNCTION '
            'hosting_controlplane.lock_authority_scope(text, text, text) TO {}',
            'GRANT SELECT ON hosting_controlplane.worker_enrollments, '
            'hosting_controlplane.worker_capabilities TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.worker_grants TO {}',
            'GRANT EXECUTE ON FUNCTION hosting_controlplane.lock_worker_scope('
            'text, text, text, text, text, text, text, text, text, text) TO {}',
            'GRANT EXECUTE ON FUNCTION '
            'hosting_controlplane.lock_native_worker_scope(text, text, text) TO {}',
            'GRANT EXECUTE ON FUNCTION hosting_controlplane.lock_job_scope('
            'text, text, text) TO {}',
            'GRANT SELECT, INSERT, UPDATE ON '
            'hosting_controlplane.native_operation_leases, '
            'hosting_controlplane.native_operation_intents TO {}',
            'GRANT SELECT, INSERT ON '
            'hosting_controlplane.native_operation_observations, '
            'hosting_controlplane.native_operation_reviews, '
            'hosting_controlplane.native_owner_recovery_reviews, '
            'hosting_controlplane.native_containment_holds TO {}',
            'GRANT SELECT, INSERT, UPDATE ON '
            'hosting_controlplane.evidence_streams TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.evidence_entries TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.environment_registrations TO {}',
            'GRANT SELECT ON hosting_controlplane.discovery_campaigns, '
            'hosting_controlplane.discovery_generations, '
            'hosting_controlplane.discovery_observations, '
            'hosting_controlplane.discovery_absence_candidates TO {}',
            'GRANT SELECT ON hosting_controlplane.assessment_inputs TO {}',
            'GRANT SELECT, INSERT ON hosting_controlplane.application_draft_revisions TO {}',
            'GRANT SELECT ON hosting_controlplane.audit_streams TO {}',
            'GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO {}',
        ):
            connection.execute(sql.SQL(statement).format(runtime))
        if authority_dsn:
            writer = sql.Identifier(conninfo_to_dict(authority_dsn)['user'])
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
        if enrollment_dsn:
            writer = sql.Identifier(conninfo_to_dict(enrollment_dsn)['user'])
            for statement in (
                'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.worker_enrollments, '
                'hosting_controlplane.worker_certificate_versions TO {}',
                'GRANT INSERT ON hosting_controlplane.worker_capabilities TO {}',
                'GRANT INSERT ON hosting_controlplane.audit_events TO {}',
                'GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO {}',
            ):
                connection.execute(sql.SQL(statement).format(writer))
        if directory_resolver_dsn:
            resolver = sql.Identifier(conninfo_to_dict(directory_resolver_dsn)['user'])
            connection.execute(sql.SQL('GRANT SELECT ON '
                'hosting_controlplane.directory_subjects, '
                'hosting_controlplane.directory_sessions, '
                'hosting_controlplane.audit_events TO {}').format(resolver))
            connection.execute(sql.SQL('GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.directory_state_digest(text, text) TO {}').format(resolver))
        if directory_writer_dsn:
            writer = sql.Identifier(conninfo_to_dict(directory_writer_dsn)['user'])
            for statement in (
                'GRANT SELECT, INSERT, UPDATE ON hosting_controlplane.directory_subjects TO {}',
                'GRANT SELECT, INSERT, DELETE ON hosting_controlplane.directory_sessions TO {}',
                'GRANT INSERT ON hosting_controlplane.directory_sync_events TO {}',
                'GRANT SELECT, INSERT ON hosting_controlplane.audit_events TO {}',
                'GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.directory_state_digest(text, text) TO {}',
                'GRANT SELECT, UPDATE ON hosting_controlplane.plan_authority_state TO {}',
                'GRANT SELECT ON hosting_controlplane.plan_approvals, '
                'hosting_controlplane.operation_jobs TO {}',
                'GRANT INSERT ON hosting_controlplane.plan_revocations TO {}',
                'GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO {}',
            ):
                connection.execute(sql.SQL(statement).format(writer))
        if site_worker_dsn:
            worker = sql.Identifier(conninfo_to_dict(site_worker_dsn)['user'])
            for statement in (
                'GRANT SELECT ON hosting_controlplane.operation_jobs, '
                'hosting_controlplane.worker_grants, '
                'hosting_controlplane.enterprise_records, '
                'hosting_controlplane.audit_events, '
                'hosting_controlplane.plan_approvals, '
                'hosting_controlplane.native_containment_holds TO {}',
                'GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.lock_job_scope(text, text, text) TO {}',
                'GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.lock_authority_scope(text, text, text) TO {}',
                'GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.lock_worker_scope('
                'text, text, text, text, text, text, text, text, text, text) TO {}',
                'GRANT EXECUTE ON FUNCTION '
                'hosting_controlplane.lock_native_worker_scope(text, text, text) TO {}',
            ):
                connection.execute(sql.SQL(statement).format(worker))
        if discovery_dsn:
            ingest = sql.Identifier(conninfo_to_dict(discovery_dsn)['user'])
            for statement in (
                'GRANT SELECT ON hosting_controlplane.environment_registrations TO {}',
                'GRANT INSERT ON hosting_controlplane.audit_events TO {}',
                'GRANT SELECT, INSERT ON hosting_controlplane.discovery_campaigns, '
                'hosting_controlplane.discovery_generations, '
                'hosting_controlplane.discovery_observations, '
                'hosting_controlplane.discovery_absence_candidates TO {}',
            ):
                connection.execute(sql.SQL(statement).format(ingest))
        if assessment_dsn:
            reviewer = sql.Identifier(conninfo_to_dict(assessment_dsn)['user'])
            for statement in (
                'GRANT SELECT ON hosting_controlplane.environment_registrations TO {}',
                'GRANT SELECT, INSERT ON hosting_controlplane.assessment_inputs TO {}',
                'GRANT INSERT ON hosting_controlplane.audit_events TO {}',
                'GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO {}',
            ):
                connection.execute(sql.SQL(statement).format(reviewer))
    print('PostgreSQL control-plane test roles and grants are ready')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
