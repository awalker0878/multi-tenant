"""Synthetic SQL interlock commissioning for a disposable PostgreSQL CI DB.

This is outside the installed package, has no signer, credentials or native
observer, and cannot satisfy OperatingInstanceGate. Its sole purpose is allowing
existing local ledger tests to exercise later native admission boundaries.
"""
from __future__ import annotations

import os

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.operations.instance import OperatingInstanceGate


def commission_isolated_instance(migration_dsn: str) -> None:
    if (os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') != '1'
            or not migration_dsn
            or migration_dsn != os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN')):
        raise RuntimeError('Explicit disposable CI migration DSN and isolation flag required')
    import psycopg
    with psycopg.connect(migration_dsn) as connection:
        # Do not destroy signed/commissioned state accidentally pointed at by
        # test configuration. Only fresh or previous synthetic CI state qualifies.
        row = connection.execute('SELECT mode,organization_id,report_event_key '
            'FROM hosting_controlplane.operating_instance WHERE singleton FOR UPDATE').fetchone()
        if row is None or (row[0] != 'UNCOMMISSIONED' and row[1:] != (
                'synthetic-ci-no-native-use', 'synthetic-ci-not-independent-evidence')):
            raise RuntimeError('CI cannot overwrite a commissioned or observation-only instance')
        connection.execute("UPDATE hosting_controlplane.operating_instance SET mode='ACTIVE',"
            'generation=generation+1,updated_at=clock_timestamp(),'
            'database_oid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),'
            "organization_id='synthetic-ci-no-native-use',tenant_id='synthetic-ci-no-native-use',"
            'source_commit=%s,artifact_sha256=%s,'
            "report_event_key='synthetic-ci-not-independent-evidence',report_sha256=%s,"
            "handover_event_key='synthetic-ci-not-accepted-handover',handover_sha256=%s,"
            "review_until=clock_timestamp()+interval '6 hours' WHERE singleton",
            ('0' * 40, '0' * 64, '0' * 64, '0' * 64))


class SyntheticIsolatedInstanceGate(OperatingInstanceGate):
    """Explicit no-native ledger-test owner; never packaged with the runtime."""
    def __init__(self, source_commit: str):
        if os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED') != '1':
            raise RuntimeError('Synthetic instance owner is only available in isolated PostgreSQL tests')
        self.source_commit, self.artifact_sha256 = source_commit, '0' * 64

    def require_write_admission(self, cursor, context, **scope):
        cursor.execute('SELECT mode,organization_id,report_event_key,'
            'database_oid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),'
            'review_until>clock_timestamp() FROM hosting_controlplane.operating_instance WHERE singleton')
        if cursor.fetchone() != ('ACTIVE', 'synthetic-ci-no-native-use',
                'synthetic-ci-not-independent-evidence', True, True):
            raise AuthorityDenied('Synthetic local SQL instance interlock is held')
        self.require_observation(cursor, context)

    def require_observation(self, cursor, context):
        cursor.execute("SELECT current_setting('app.organization_id',true),"
                       "current_setting('app.tenant_id',true)")
        if cursor.fetchone() != (context.organization_id, context.tenant_id):
            raise AuthorityDenied('Synthetic local observation context changed')
