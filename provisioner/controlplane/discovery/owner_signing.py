"""Installed, offline application-owner decision preparation and signing.

Consumes the existing immutable draft and assessment evidence contracts. No
network, enrollment issuance, SQL, platform operation or ingestion is performed.
Owner private keys stay on a separately administered POSIX signing workstation.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import Callable

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .application_drafts import parse_draft_export
from .application_review import DECISIONS, REVIEW_KIND, require_draft_binding
from .assessment_inputs import AssessmentInputDenied, SignedFileAssessmentTrustStore, parse_evidence
from .model import _id, _json, _scope_json, _utc
from .native_credentials import decode_json
from .trust import _decode, _keys

MAX_EXPORT_BYTES = 262144
MAX_EVIDENCE_BYTES = 65536
MAX_CONFIG_BYTES = 65536


@contextmanager
def _parent(value: str):
    """Open each ancestor without following links; final parent is private.

    Root-owned sticky ancestors (e.g. /tmp) are allowed, never as the final
    parent. No directory is created and unsupported OS primitives fail closed.
    """
    path = Path(value)
    if (os.name != 'posix' or not isinstance(value, str) or not 1 <= len(value) <= 4096
            or not path.is_absolute() or str(path) != value or value.startswith('//')
            or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(part in ('.', '..') for part in path.parts) or len(path.parts) < 2):
        raise ValueError('An exact absolute POSIX file path is required')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    try:
        for part in path.parts[1:-1]:
            info = os.fstat(fd)
            if (info.st_uid not in (0, os.geteuid())
                    or info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX)):
                raise ValueError('Unsafe review ancestor')
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o077:
            raise ValueError('Review files require a private parent directory')
        yield fd, path.name
    finally:
        os.close(fd)


def _read(path: str, limit: int) -> bytes:
    with _parent(path) as (parent, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=parent)
        try:
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid not in (0, os.geteuid())
                    or before.st_mode & 0o077 or before.st_nlink != 1 or not 1 <= before.st_size <= limit):
                raise ValueError('Review input must be a bounded private regular file')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(limit + 1)
            after = os.fstat(fd)
            if (len(raw) != before.st_size or len(raw) > limit
                    or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                       (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
                raise ValueError('Review input changed during reading')
            return raw
        finally:
            os.close(fd)


def _publish(path: str, raw: bytes, recheck: Callable[[], None]) -> None:
    """Create once, never replace. Failed post-link fsync leaves original output.

    A failure is not proof that no final file exists. Do not delete or overwrite
    that file on a retry; reconcile its exact bytes independently.
    """
    with _parent(path) as (parent, name):
        temporary = '.review-' + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            recheck()
            os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        finally:
            os.close(fd)
            os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)


def prepare_review(stored, *, evidence_id: str, evidence_revision: int, decision: str,
                   review_reference: str, ttl_seconds: int, checked_at: datetime):
    """Build the existing unsigned envelope, not a claim of server currency."""
    if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 3600 or not _utc(checked_at):
        raise ValueError('A current UTC clock and bounded review lifetime are required')
    payload = {'environmentId': stored.environment_id, 'scope': _scope_json(stored.scope),
        'applicationGroupId': stored.application_group_id, 'draftRevision': stored.revision,
        'draftRecordDigest': stored.record_digest, 'generation': stored.generation,
        'resultDigest': stored.result_digest, 'proposalDigest': stored.proposal_digest,
        'ownerId': json.loads(stored.proposal_json)['draft']['ownerId'], 'decision': decision,
        'reviewReference': review_reference, 'reviewedAt': checked_at.isoformat()}
    evidence = parse_evidence({'format': 'hosting-assessment-evidence/1', 'kind': REVIEW_KIND,
        'evidenceId': evidence_id, 'revision': evidence_revision,
        'issuedAt': checked_at.isoformat(),
        'expiresAt': (checked_at + timedelta(seconds=ttl_seconds)).isoformat(), 'payload': payload})
    require_draft_binding(evidence.value, stored)
    return evidence


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # Never echo a mistaken credential value or input path in an error.
        raise ValueError('Invalid owner-review command')


def build_parser():
    parser = _Parser(prog='hosting-application-review',
                     description='Prepare or sign an offline, assessment-only owner decision.')
    actions = parser.add_subparsers(dest='action', required=True)
    for action in ('prepare', 'sign'):
        command = actions.add_parser(action)
        command.add_argument('--draft-file', required=True)
        command.add_argument('--record-digest', required=True,
                             help='Exact recordDigest independently reviewed with the full exported draft')
        command.add_argument('--output', required=True, help='New private file; never overwritten')
        if action == 'prepare':
            command.add_argument('--evidence-id', required=True)
            command.add_argument('--evidence-revision', required=True, type=int)
            command.add_argument('--decision', required=True, choices=sorted(DECISIONS))
            command.add_argument('--review-reference', required=True)
            command.add_argument('--ttl-seconds', required=True, type=int)
        else:
            command.add_argument('--decision-file', required=True)
            command.add_argument('--confirm-evidence-digest', required=True,
                                 help='Confirm the complete prepared canonical evidence digest')
            command.add_argument('--config', required=True,
                                 help='Protected owner signing configuration; never key bytes in argv')
    return parser


def run(args, *, clock: Callable[[], datetime]) -> dict:
    last = None

    def now():
        nonlocal last
        current = clock()
        if not _utc(current) or last is not None and current < last:
            raise ValueError('Owner signing clock is unavailable or regressed')
        last = current
        return current

    now()
    draft_raw = _read(args.draft_file, MAX_EXPORT_BYTES)
    exported = decode_json(draft_raw, MAX_EXPORT_BYTES)
    stored = parse_draft_export(exported, expected_record_digest=args.record_digest)
    if args.action == 'prepare':
        evidence = prepare_review(stored, evidence_id=args.evidence_id,
            evidence_revision=args.evidence_revision, decision=args.decision,
            review_reference=args.review_reference, ttl_seconds=args.ttl_seconds, checked_at=now())
    else:
        decision_raw = _read(args.decision_file, MAX_EVIDENCE_BYTES)
        evidence = parse_evidence(decode_json(decision_raw, MAX_EVIDENCE_BYTES))
        if (evidence.kind != REVIEW_KIND or evidence.digest != args.confirm_evidence_digest
                or decision_raw != evidence.canonical_json.encode('ascii')):
            raise ValueError('Confirmed canonical owner evidence is required')
        require_draft_binding(evidence.value, stored)
    if evidence.value.decision == 'ACCEPT_FOR_ASSESSMENT' and exported['sourceSuperseded']:
        raise ValueError('A superseded source export cannot be accepted')

    def recheck_inputs():
        if _read(args.draft_file, MAX_EXPORT_BYTES) != draft_raw:
            raise ValueError('The reviewed draft export changed')
        at = now()
        if not evidence.issued_at <= at < evidence.expires_at:
            raise ValueError('The prepared decision is no longer current')
        return at

    if args.action == 'prepare':
        raw = evidence.canonical_json.encode('ascii')
        _publish(args.output, raw, recheck_inputs)
        status = 'PREPARED_UNSIGNED'
    else:
        config_raw = _read(args.config, MAX_CONFIG_BYTES)
        config = _keys(decode_json(config_raw, MAX_CONFIG_BYTES), {'format', 'trust', 'signer'})
        trust_config = _keys(config['trust'], {'policyFile', 'rootKey', 'minimumRevision'})
        signer = _keys(config['signer'], {'keyFile', 'keyId'})
        if (config['format'] != 'hosting-application-review-signer/1' or not _id(signer['keyId'])
                or type(trust_config['minimumRevision']) is not int
                or not 1 <= trust_config['minimumRevision'] < 2**63):
            raise ValueError('Protected exact owner signing configuration is required')
        _read(trust_config['policyFile'], 1048576)
        trust = SignedFileAssessmentTrustStore(trust_config['policyFile'],
            authority_public_key=Ed25519PublicKey.from_public_bytes(_decode(trust_config['rootKey'], 32)),
            minimum_revision=trust_config['minimumRevision'])
        key_raw = _read(signer['keyFile'], 32)
        key = Ed25519PrivateKey.from_private_bytes(key_raw)
        trust.authorize_application_signer(evidence, signer['keyId'], key.public_key().public_bytes_raw(),
                                           recheck_inputs())
        signatures = ({'keyId': signer['keyId'], 'signature': base64.b64encode(
            key.sign(evidence.canonical_json.encode('ascii'))).decode('ascii')},)

        def recheck_signature():
            recheck_inputs()
            if (_read(args.config, MAX_CONFIG_BYTES) != config_raw
                    or _read(args.decision_file, MAX_EVIDENCE_BYTES) != decision_raw
                    or _read(signer['keyFile'], 32) != key_raw):
                raise ValueError('Signing inputs changed during the operation')
            _read(trust_config['policyFile'], 1048576)
            # Read current root-signed enrollment again; no earlier-success cache.
            trust.verify(evidence, signatures, now())

        recheck_signature()
        raw = _json({'evidence': json.loads(evidence.canonical_json), 'signatures': signatures}).encode('ascii')
        _publish(args.output, raw, recheck_signature)
        status = 'SIGNED_NOT_INGESTED'
    return {'status': status, 'evidenceId': evidence.evidence_id, 'evidenceRevision': evidence.revision,
        'evidenceDigest': evidence.digest, 'outputDigest': hashlib.sha256(raw).hexdigest(),
        'draftRecordDigest': stored.record_digest, 'proposalDigest': stored.proposal_digest,
        'decision': evidence.value.decision, 'ownerId': evidence.value.owner_id,
        'expiresAt': evidence.expires_at.isoformat(), 'ingested': False,
        'dependencyEvidenceVerified': False, 'ownershipAccepted': False, 'executionAuthorized': False}


def main(argv=None, *, clock=lambda: datetime.now(timezone.utc), stdout=None, stderr=None) -> int:
    out, err = stdout or sys.stdout, stderr or sys.stderr
    try:
        result = run(build_parser().parse_args(argv), clock=clock)
        out.write(_json(result) + '\n')
        return 0
    except KeyboardInterrupt:
        err.write('{"error":"OWNER_REVIEW_INTERRUPTED","outputMayExist":true}\n')
        return 130
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, AssessmentInputDenied, UnsupportedAlgorithm):
        err.write('{"error":"OWNER_REVIEW_HELD","outputMayExist":true}\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
