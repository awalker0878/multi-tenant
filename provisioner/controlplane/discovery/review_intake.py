"""One-shot custodian intake of an already signed application-owner decision.

Only the existing AssessmentInputRepository may append evidence. This process
has no owner signing key, public listener, source lookup or native action path.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
import re
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.persistence.store import TenantContext
from . import review_files
from .application_review import REVIEW_KIND
from .assessment_inputs import (AssessmentInputDenied, AssessmentInputRepository,
                               SignedFileAssessmentTrustStore, _parse_scope, parse_evidence)
from .model import _id, _json, _scope_json, _utc
from .native_credentials import decode_json
from .trust import _decode, _keys

MAX_SUBMISSION_BYTES = 71680
_ROLE = re.compile(r'[a-z][a-z0-9_]{0,62}\Z')
_READ = ('assessment_inputs', 'environment_registrations',
         'application_draft_revisions', 'discovery_generations', 'discovery_observations')
_WRITE = ('assessment_inputs', 'audit_events')


def parse_submission(raw: bytes, expected_digest: str):
    """Only the unchanged signer artifact, never arbitrary assessment evidence."""
    if (not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_SUBMISSION_BYTES
            or not isinstance(expected_digest, str)
            or not re.fullmatch(r'[0-9a-f]{64}', expected_digest)
            or hashlib.sha256(raw).hexdigest() != expected_digest):
        raise ValueError('Exact reviewed submission bytes required')
    value = _keys(decode_json(raw, MAX_SUBMISSION_BYTES), {'evidence', 'signatures'})
    evidence = parse_evidence(value['evidence'])
    if (evidence.kind != REVIEW_KIND or _json(value).encode('ascii') != raw
            or not isinstance(value['signatures'], list) or len(value['signatures']) != 1):
        raise ValueError('Canonical application-owner submission required')
    signature = _keys(value['signatures'][0], {'keyId', 'signature'})
    if not _id(signature['keyId']):
        raise ValueError('An exact signing key is required')
    _decode(signature['signature'], 64)
    return evidence, (signature,)


def connection_parameters(database: dict, password: bytes) -> dict:
    """A closed PostgreSQL 17+ TLS/SCRAM contract; no DSN or service overrides."""
    _keys(database, {'host', 'hostaddr', 'port', 'name', 'role', 'passwordFile', 'caFile', 'crlFile'})
    address = ipaddress.ip_address(database['hostaddr'])
    if (not isinstance(database['host'], str)
            or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?', database['host'])
            or '..' in database['host'] or type(database['port']) is not int
            or not 1 <= database['port'] <= 65535
            or not isinstance(database['name'], str) or not _ROLE.fullmatch(database['name'])
            or not isinstance(database['role'], str) or not _ROLE.fullmatch(database['role'])
            or str(address) != database['hostaddr'] or address.is_multicast or address.is_unspecified
            or '%' in database['hostaddr'] or not isinstance(password, bytes)
            or not 1 <= len(password) <= 4096 or any(not 33 <= c <= 126 for c in password)):
        raise ValueError('Exact protected database settings required')
    return dict(host=database['host'], hostaddr=database['hostaddr'], port=database['port'],
        dbname=database['name'], user=database['role'], password=password.decode('ascii'),
        sslrootcert=database['caFile'], sslcrl=database['crlFile'], sslmode='verify-full',
        sslcertmode='disable', ssl_min_protocol_version='TLSv1.2',
        require_auth='scram-sha-256', channel_binding='require', gssencmode='disable',
        passfile='/dev/null', connect_timeout=5, client_encoding='UTF8',
        options='-c statement_timeout=10000 -c lock_timeout=5000',
        application_name='hosting-application-review-ingest', autocommit=False)


def _connect_database(parameters):
    # libpq environment defaults must not add another endpoint, service or credential.
    if any(key.startswith('PG') for key in os.environ) or os.environ.get('SSLKEYLOGFILE'):
        raise ValueError('Ambient database or TLS key-logging configuration is forbidden')
    import psycopg
    if psycopg.pq.version() < 170000:
        raise ValueError('The selected intake transport requires libpq 17 or newer')
    return psycopg.connect(**parameters)


def require_intake_login(connection, role):
    """Check the actual session, not merely the configured login spelling."""
    def require(sql, expected, parameters=None):
        if connection.execute(sql, parameters).fetchone() != expected:
            raise AssessmentInputDenied('Dedicated append-only intake login required')
    if connection.autocommit:
        raise AssessmentInputDenied('Transactional intake required')
    require('SELECT current_user, session_user, rolsuper, rolbypassrls, rolcreaterole, '
            'rolcreatedb, rolreplication FROM pg_catalog.pg_roles WHERE rolname=current_user',
            (role, role, False, False, False, False, False))
    require('SELECT hosting_controlplane.is_site_worker_role()', (False,))
    require('SELECT coalesce(bool_or(pg_has_role(session_user, r.oid, %s)), false) '
            'FROM pg_catalog.pg_roles r WHERE r.rolname <> session_user', (False,), ('member',))
    require("SELECT has_database_privilege(current_user,current_database(),'CREATE'), "
            "coalesce(bool_or(has_schema_privilege(current_user,n.oid,'CREATE')),false) "
            "FROM pg_catalog.pg_namespace n WHERE left(n.nspname,3)<>'pg_' "
            "AND n.nspname <> 'information_schema'", (False, False))
    require("SELECT coalesce(bool_or(has_table_privilege(current_user,c.oid,'UPDATE') "
            "OR has_table_privilege(current_user,c.oid,'DELETE') "
            "OR has_table_privilege(current_user,c.oid,'TRUNCATE') "
            "OR has_table_privilege(current_user,c.oid,'TRIGGER') "
            "OR has_table_privilege(current_user,c.oid,'REFERENCES') "
            "OR (has_table_privilege(current_user,c.oid,'INSERT') AND NOT "
            "(n.nspname='hosting_controlplane' AND c.relname=ANY(%s)))),false) "
            "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "WHERE c.relkind IN ('r','p') AND left(n.nspname,3)<>'pg_' "
            "AND n.nspname <> 'information_schema'", (False,), (list(_WRITE),))
    # Table checks alone do not reject a column-only UPDATE or foreign INSERT grant.
    require("SELECT coalesce(bool_or(has_column_privilege(current_user,c.oid,a.attnum,'UPDATE') "
            "OR has_column_privilege(current_user,c.oid,a.attnum,'REFERENCES') "
            "OR (has_column_privilege(current_user,c.oid,a.attnum,'INSERT') AND NOT "
            "(n.nspname='hosting_controlplane' AND c.relname=ANY(%s)))),false) "
            "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid "
            "WHERE c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped "
            "AND left(n.nspname,3)<>'pg_' AND n.nspname <> 'information_schema'",
            (False,), (list(_WRITE),))
    require("SELECT bool_and(coalesce(has_table_privilege(current_user, "
            "to_regclass('hosting_controlplane.'||t.name),'SELECT'),false)) "
            "FROM unnest(%s::text[]) AS t(name)", (True,), (list(_READ),))
    require("SELECT bool_and(coalesce(has_table_privilege(current_user, "
            "to_regclass('hosting_controlplane.'||t.name),'INSERT'),false)) "
            "FROM unnest(%s::text[]) AS t(name)", (True,), (list(_WRITE),))
    require("SELECT count(*)=6 AND coalesce(bool_and(c.relrowsecurity AND c.relforcerowsecurity),false) "
            "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='hosting_controlplane' AND c.relname=ANY(%s)",
            (True,), ([*_READ, 'audit_events'],))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Invalid review intake command')


def build_parser():
    parser = _Parser(prog='hosting-application-review-ingest',
        description='Record one signed owner decision through the existing assessment custodian.')
    for name in ('config', 'submission-file', 'submission-digest', 'receipt'):
        parser.add_argument('--' + name, required=True)
    return parser


def run(args, state: dict, *, clock):
    frozen = {}
    def read(path, maximum):
        raw = review_files.read_private(path, maximum)
        if path in frozen and frozen[path][0] != raw:
            raise ValueError('Aliased intake input changed')
        frozen[path] = (raw, maximum)
        return raw
    def unchanged():
        for path, (raw, maximum) in frozen.items():
            if review_files.read_private(path, maximum) != raw:
                raise ValueError('Intake inputs changed')
    last = None
    def now():
        nonlocal last
        at = clock()
        if not _utc(at) or last is not None and at < last:
            raise ValueError('Intake clock unavailable or regressed')
        last = at
        return at
    now()
    value = _keys(decode_json(read(args.config, 65536), 65536),
                  {'format', 'environmentId', 'scope', 'database', 'trust'})
    if value['format'] != 'hosting-application-review-ingest/1' or not _id(value['environmentId']):
        raise ValueError('Protected exact intake configuration required')
    scope = _parse_scope(value['scope'])
    trust_config = _keys(value['trust'], {'policyFile', 'rootKey', 'minimumRevision'})
    if type(trust_config['minimumRevision']) is not int or not 1 <= trust_config['minimumRevision'] < 2**63:
        raise ValueError('Protected policy floor required')
    trust = SignedFileAssessmentTrustStore(trust_config['policyFile'],
        authority_public_key=Ed25519PublicKey.from_public_bytes(_decode(trust_config['rootKey'], 32)),
        minimum_revision=trust_config['minimumRevision'])
    raw = read(args.submission_file, MAX_SUBMISSION_BYTES)
    evidence, signatures = parse_submission(raw, args.submission_digest)
    if evidence.environments != ((value['environmentId'], scope),):
        raise AssessmentInputDenied('Submission is outside the configured intake scope')
    def recheck():
        unchanged()
        review_files.read_private(trust_config['policyFile'], 1048576)
        trust.verify(evidence, signatures, now())
    recheck()  # Refuse bad signatures/scope before reading a database password.
    database = _keys(value['database'],
        {'host', 'hostaddr', 'port', 'name', 'role', 'passwordFile', 'caFile', 'crlFile'})
    parameters = connection_parameters(database, read(database['passwordFile'], 4096))
    for key in ('caFile', 'crlFile'):
        read(database[key], 1048576)
    review_files.require_new_output(args.receipt)

    @contextmanager
    def connect():
        recheck()
        with _connect_database(parameters) as connection:
            require_intake_login(connection, database['role'])
            recheck()
            state['attempted'] = True
            yield connection
            recheck()  # Still inside the DB context: a hold rolls back before COMMIT.

    repository = AssessmentInputRepository(connect, trust, ingest_role=database['role'])
    digest = repository.ingest(TenantContext(scope.organization_id, scope.tenant_id),
                               json.loads(evidence.canonical_json), signatures)
    if digest != evidence.digest:
        raise ValueError('Unexpected ingestion acknowledgement')
    state['recorded'] = True  # Repository's connection context has committed successfully.
    receipt = {'format': 'hosting-application-review-receipt/1', 'status': 'RECORDED_ASSESSMENT_ONLY',
        'environmentId': value['environmentId'], 'scope': _scope_json(scope),
        'applicationGroupId': evidence.value.application_group_id,
        'draftRevision': evidence.value.draft_revision, 'draftRecordDigest': evidence.value.draft_record_digest,
        'evidenceId': evidence.evidence_id, 'evidenceRevision': evidence.revision,
        'evidenceDigest': evidence.digest, 'submissionDigest': args.submission_digest,
        'decision': evidence.value.decision, 'acknowledgedAt': now().isoformat(),
        'dependencyEvidenceVerified': False, 'ownershipAccepted': False, 'executionAuthorized': False}
    # Receipt means committed ingestion, not continuing review validity. Do not
    # turn post-commit expiry/revocation into a claim that the write rolled back.
    review_files.publish_once(args.receipt, _json(receipt).encode('ascii'), unchanged)
    return receipt


def main(argv=None, *, clock=lambda: datetime.now(timezone.utc), stdout=None, stderr=None):
    out, err = stdout or sys.stdout, stderr or sys.stderr
    state = {'attempted': False, 'recorded': False}
    try:
        receipt = run(build_parser().parse_args(argv), state, clock=clock)
        out.write(_json(receipt) + '\n')
        return 0
    except KeyboardInterrupt:
        code, error = 130, 'REVIEW_INTAKE_INTERRUPTED'
    except Exception:
        # The CLI boundary must redact driver/SQL/custody errors and credentials.
        code = 3 if state['attempted'] else 2
        error = 'REVIEW_INTAKE_UNKNOWN' if state['attempted'] else 'REVIEW_INTAKE_HELD'
    err.write(_json({'error': error, 'ingestAttempted': state['attempted'],
                    'recorded': state['recorded'], 'outputMayExist': True}) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
